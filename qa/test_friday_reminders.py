from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from friday_reminders import create_reminder, resolve_time


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2030, 1, 1, 23, 45, tzinfo=timezone(timedelta(hours=-4)))

    def test_relative_minutes_cross_midnight_without_timezone_guessing(self):
        self.assertEqual(resolve_time(minutes=30, now=self.now), self.now + timedelta(minutes=30))

    def test_relative_bounds_and_absolute_timezone(self):
        for minutes in (0, -1, True, 525601):
            with self.subTest(minutes=minutes), self.assertRaises(ValueError):
                resolve_time(minutes=minutes, now=self.now)
        for value in ('2030-01-02T01:00:00', 'bad', '2029-01-01T00:00:00Z'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_time(at=value, now=self.now)
        self.assertIsNotNone(resolve_time(at='2030-01-03T00:00:00-04:00', now=self.now).tzinfo)

    @patch('friday_reminders.gateway')
    def test_dry_run_never_creates_or_sends(self, gateway):
        result = create_reminder(self.now, 'Prueba', dry_run=True)
        gateway.assert_not_called()
        self.assertFalse(result['scheduled'])

    @patch('friday_reminders.gateway')
    def test_duplicate_does_not_schedule_again(self, gateway):
        gateway.side_effect = [{'jobs': []}, {'id': 'test-job', 'enabled': True}]
        create_reminder(self.now, 'Prueba')
        job = gateway.call_args.args[1]
        gateway.reset_mock()
        gateway.side_effect = None
        gateway.return_value = {'jobs': [{**job, 'id': 'test-job', 'enabled': False}]}
        result = create_reminder(self.now, 'Prueba')
        self.assertEqual(result['id'], 'test-job')
        self.assertFalse(result['enabled'])
        self.assertEqual(gateway.call_count, 1)

    @patch('friday_reminders.gateway')
    def test_message_is_an_exact_argv_argument(self, gateway):
        gateway.side_effect = [{'jobs': []}, {'id': 'test-job', 'enabled': True}]
        message = "Recuerda: 'hola'; $() & no ejecutar"
        create_reminder(self.now, message)
        job = gateway.call_args.args[1]
        self.assertEqual(job['payload']['argv'][-1], message)
        self.assertEqual(job['payload']['kind'], 'command')
        self.assertTrue(job['deleteAfterRun'])

    @patch('friday_reminders.gateway')
    def test_missing_confirmation_is_not_reported_as_success(self, gateway):
        gateway.side_effect = [{'jobs': []}, {'ok': True}]
        with self.assertRaises(RuntimeError):
            create_reminder(self.now, 'Prueba')


if __name__ == '__main__':
    unittest.main()
