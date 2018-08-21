from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from workplace.models import Reservation

from .exceptions import PaymentAPIError
from .models import (Package, Membership, Order, OrderLine, BaseProduct,
                     CreditCard, PaymentProfile)
from .services import (charge_payment,
                       create_external_payment_profile,
                       create_external_card,
                       get_external_cards,)


class BaseProductSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    order_lines = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='orderline-detail'
    )
    price = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0.1,
    )

    def to_representation(self, instance):
        user = self.context['request'].user
        data = super(BaseProductSerializer, self).to_representation(instance)
        if not user.is_staff:
            data.pop("order_lines")
        return data

    class Meta:
        model = BaseProduct
        fields = '__all__'
        abstract = True


class MembershipSerializer(BaseProductSerializer):
    class Meta:
        model = Membership
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the membership."),
                'validators': [
                    UniqueValidator(queryset=Membership.objects.all())
                ],
            },
        }


class PackageSerializer(BaseProductSerializer):
    reservations = serializers.IntegerField(
        min_value=1,
    )

    class Meta:
        model = Package
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the package."),
                'validators': [
                    UniqueValidator(queryset=Package.objects.all())
                ],
            },
        }


class CreditCardSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = CreditCard
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the credit card."),
                'validators': [
                    UniqueValidator(queryset=CreditCard.objects.all())
                ],
            },
        }


class PaymentProfileSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    cards = serializers.SerializerMethodField()

    def get_cards(self, obj):
        return get_external_cards(obj.external_api_id)

    class Meta:
        model = PaymentProfile
        fields = (
            'id',
            'name',
            'owner',
            'cards',
        )
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the payment profile."),
                'validators': [
                    UniqueValidator(queryset=PaymentProfile.objects.all())
                ],
            },
        }


class OrderLineSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.all(),
        slug_field='model',
    )

    def validate(self, attrs):
        """Limits packages according to request user membership"""
        validated_data = super().validate(attrs)

        user_membership = self.context['request'].user.membership

        content_type = validated_data.get(
            'content_type',
            getattr(self.instance, 'content_type', None)
        )
        object_id = validated_data.get(
            'object_id',
            getattr(self.instance, 'object_id', None)
        )
        try:
            obj = content_type.get_object_for_this_type(pk=object_id)
        except content_type.model_class().DoesNotExist:
            raise serializers.ValidationError({
                'object_id': [
                    _("The referenced object does not exist.")
                ],
            })

        if (not self.context['request'].user.is_staff and
                content_type.model == 'package' and
                obj.exclusive_memberships.all() and
                user_membership not in obj.exclusive_memberships.all()):
            raise serializers.ValidationError({
                'object_id': [
                    _(
                        "User does not have the required membership to order "
                        "this package."
                    )
                ],
            })

        return attrs

    class Meta:
        model = OrderLine
        fields = '__all__'


class OrderLineSerializerNoOrder(OrderLineSerializer):
    class Meta:
        model = OrderLine
        fields = '__all__'
        extra_kwargs = {
            'order': {
                'read_only': True,
            },
        }


class OrderSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    authorization_id = serializers.ReadOnlyField()
    settlement_id = serializers.ReadOnlyField()
    order_lines = OrderLineSerializerNoOrder(many=True)
    payment_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True
    )
    single_use_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True
    )

    @transaction.atomic()
    def create(self, validated_data):
        """
        Create an Order and charge the user.
        """
        user = self.context['request'].user
        orderlines_data = validated_data.pop('order_lines')
        payment_token = validated_data.pop('payment_token', None)
        single_use_token = validated_data.pop('single_use_token', None)
        # Temporary IDs until the external profile is created.
        validated_data['authorization_id'] = "0"
        validated_data['settlement_id'] = "0"
        validated_data['transaction_date'] = timezone.now()
        validated_data['user'] = user

        order = Order.objects.create(**validated_data)
        for orderline_data in orderlines_data:
            OrderLine.objects.create(order=order, **orderline_data)
        amount = int(round(order.total_cost*100))

        if payment_token:
            # Charge the order with the external payment API
            try:
                charge_response = charge_payment(
                    amount,
                    payment_token,
                    str(order.id)
                )
            except PaymentAPIError as err:
                raise serializers.ValidationError({
                    'message': err
                })

        elif single_use_token:
            # Try to get existing PaymentProfile
            profile = PaymentProfile.objects.filter(owner=order.user).first()
            if profile:
                # Add card to the external profile
                try:
                    card_create_response = create_external_card(
                        profile.external_api_id,
                        single_use_token
                    )
                    charge_response = charge_payment(
                        amount,
                        card_create_response.json()['paymentToken'],
                        str(order.id)
                    )
                except PaymentAPIError as err:
                    raise serializers.ValidationError({
                        'message': err
                    })

            else:
                # Else create a new profile with the provided single_use_token
                try:
                    create_profile_response = create_external_payment_profile(
                        single_use_token,
                        order.user
                    )
                except PaymentAPIError as err:
                    raise serializers.ValidationError({
                        'message': err
                    })

                profile = PaymentProfile.objects.create(
                    name="Paysafe",
                    owner=order.user,
                    external_api_id=create_profile_response.json()['id'],
                    external_api_url='{0}{1}'.format(
                        create_profile_response.url,
                        create_profile_response.json()['id']
                    )
                )
                try:
                    charge_response = charge_payment(
                        amount,
                        create_profile_response
                        .json()['cards'][0]['paymentToken'],
                        str(order.id)
                    )
                except PaymentAPIError as err:
                    raise serializers.ValidationError({
                        'message': err
                    })

        else:
            raise serializers.ValidationError({
                'non_field_errors': [_(
                    "A payment_token or single_use_token is required to "
                    "create an order."
                )]
            })

        order.authorization_id = charge_response.json()['id']
        order.settlement_id = charge_response.json()['settlements'][0]['id']
        order.save()

        user = order.user
        membership_orderlines = order.order_lines.filter(
            content_type__model="membership"
        )
        package_orderlines = order.order_lines.filter(
            content_type__model="package"
        )
        reservation_orderlines = order.order_lines.filter(
            content_type__model="timeslot"
        )
        if membership_orderlines:
            user.membership = membership_orderlines[0].content_object
        if package_orderlines:
            for package_orderline in package_orderlines:
                user.tickets += (
                    package_orderline.content_object.reservations *
                    package_orderline.quantity
                )
        if reservation_orderlines:
            for reservation_orderline in reservation_orderlines:
                Reservation.objects.create(
                    user=user,
                    timeslot=reservation_orderline.content_object,
                    is_active=True
                )
                user.tickets -= 1
        user.save()
        return order

    def update(self, instance, validated_data):
        orderlines_data = validated_data.pop('order_lines')
        order = super().update(instance, validated_data)
        for orderline_data in orderlines_data:
            OrderLine.objects.update_or_create(
                order=order,
                content_type=orderline_data.get('content_type'),
                object_id=orderline_data.get('object_id'),
                defaults=orderline_data,
            )
        return order

    class Meta:
        model = Order
        fields = '__all__'
        extra_kwargs = {
            'transaction_date': {
                'read_only': True,
            },
            'user': {
                'read_only': True,
            },
        }
