import json

import pytz
from django.conf import settings
from rest_framework.test import APIClient, APITestCase
from blitz_api.factories import UserFactory, AdminFactory

from datetime import timedelta, datetime

from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from blitz_api.models import AcademicLevel

from ..models import Membership, Order, OrderLine, Package

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class OrderLineStatsTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.admin = AdminFactory()
        self.package_type = ContentType.objects.get_for_model(Package)
        self.academic_level = AcademicLevel.objects.create(
            name="University"
        )
        self.membership_with_academic_level = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )
        self.membership_with_academic_level.academic_levels.set([
            self.academic_level
        ])
        self.membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )
        self.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=40,
            reservations=100,
        )
        self.package.exclusive_memberships.set([
            self.membership,
        ])
        self.order = Order.objects.create(
            user=self.user,
            transaction_date=LOCAL_TIMEZONE.localize(datetime(2020, 1, 15, 8)),
            authorization_id=1,
            settlement_id=1,
        )
        self.order_admin = Order.objects.create(
            user=self.admin,
            transaction_date=LOCAL_TIMEZONE.localize(datetime(2020, 1, 15, 8)),
            authorization_id=1,
            settlement_id=1,
        )
        self.order_line = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.package_type,
            object_id=self.package.id,
            cost=self.package.price,
        )
        self.order_line_admin = OrderLine.objects.create(
            order=self.order_admin,
            quantity=99,
            content_type=self.package_type,
            object_id=self.package.id,
            cost=99 * self.package.price,
        )

    def test_chartJS(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'orderline-chartjs'
            ) + '?interval=day&aggregate=sum',
        )

        content = {
            'labels': ['2020-01-15T00:00:00-05:00'],
            'datasets': [
                {
                    'label': 'Package',
                    'data':
                        [
                            {
                                'x': '2020-01-15T00:00:00-05:00',
                                'y': 100
                            }
                        ]
                }
            ]
        }

        self.assertEqual(json.loads(response.content), content)

    def test_chartJS_interval_month(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'orderline-chartjs'
            ) + '?interval=month&aggregate=sum',
        )

        content = {
            'labels': ['2020-01-01T00:00:00-05:00'],
            'datasets': [
                {
                    'label': 'Package',
                    'data': [
                        {
                            'x': '2020-01-01T00:00:00-05:00',
                            'y': 100
                        }
                    ]
                }
            ]
        }

        self.assertEqual(json.loads(response.content), content)

    def test_chartJS_interval_month_filter_date(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'orderline-chartjs'
            ) + '?interval=month&aggregate=sum' +
            'start=2018-01-01T00:00:00.000Z' +
            'end=2024-01-01T00:00:00.000Z'
        )

        content = {
            'labels': ['2020-01-01T00:00:00-05:00'],
            'datasets': [
                {
                    'label': 'Package',
                    'data': [
                        {
                            'x': '2020-01-01T00:00:00-05:00',
                            'y': 100
                        }
                    ]
                }
            ]
        }

        self.assertEqual(json.loads(response.content), content)

    def test_chartJS_interval_month_content_type_filter(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'orderline-chartjs'
            ) + '?interval=month&aggregate=sum&content_type=' +
            str(self.package_type.id),
        )

        content = {
            'labels': ['2020-01-01T00:00:00-05:00'],
            'datasets': [
                {
                    'label': 'Package',
                    'data': [
                        {
                            'x': '2020-01-01T00:00:00-05:00',
                            'y': 100
                        }
                    ]
                }
            ]
        }

        self.assertEqual(json.loads(response.content), content)

    def test_chartJS_interval_month_with_detail(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'orderline-chartjs'
            ) + '?interval=month&aggregate=sum&group_by_object=True',
        )

        content = {'labels': ['2020-01-01T00:00:00-05:00'], 'datasets': [
            {'label': 'extreme_package',
             'data': [{'x': '2020-01-01T00:00:00-05:00', 'y': 100}]}]}

        self.assertEqual(json.loads(response.content), content)

    def test_chartJS_interval_week(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'orderline-chartjs'
            ) + '?interval=week&aggregate=sum',
        )

        content = {'labels': ['2020-01-13T00:00:00-05:00'], 'datasets': [
            {'label': 'Package',
             'data': [{'x': '2020-01-13T00:00:00-05:00', 'y': 100}]}]}

        self.assertEqual(json.loads(response.content), content)

    def test_chartJS_interval_year(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'orderline-chartjs'
            ) + '?interval=year&aggregate=sum',
        )

        content = {'labels': ['2020-01-01T00:00:00-05:00'], 'datasets': [
            {'label': 'Package',
             'data': [{'x': '2020-01-01T00:00:00-05:00', 'y': 100}]}]}

        self.assertEqual(json.loads(response.content), content)

    def test_chartJS_interval_month_count(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'orderline-chartjs'
            ) + '?interval=month&aggregate=count',
        )

        content = {'labels': ['2020-01-01T00:00:00-05:00'], 'datasets': [
            {'label': 'Package',
             'data': [{'x': '2020-01-01T00:00:00-05:00', 'y': 2}]}]}

        self.assertEqual(json.loads(response.content), content)
