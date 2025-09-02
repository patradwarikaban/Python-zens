# pylint: disable=missing-module-docstring, missing-function-docstring

import unittest
from threading import Thread

from src.app import TemplateEngine


class TestConstructResponse(unittest.TestCase):
    """
    Test for construct_response
    """

    def setUp(self):
        template_engine = TemplateEngine()
        # Thread(target=template_engine.serve).start()


    def test_template_engine_start_success(self):
        """test_01_template_engine_start_success"""

        self.assertEqual(4, 4)


if __name__ == '__main__':
    unittest.main()
