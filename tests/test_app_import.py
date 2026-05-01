import unittest

from app import app


class AppImportTestCase(unittest.TestCase):
    def test_app_object_exists(self):
        self.assertIsNotNone(app)
        self.assertTrue(hasattr(app, 'run'))


if __name__ == '__main__':
    unittest.main()
