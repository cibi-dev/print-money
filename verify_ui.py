
import os
import sys
import unittest
from unittest.mock import MagicMock

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Mock modules that might cause issues in a head-less environment or require complex setup
sys.modules['db_manager'] = MagicMock()
sys.modules['utils.notifications'] = MagicMock()
sys.modules['utils.export'] = MagicMock()
sys.modules['utils.pdf_invoice'] = MagicMock()
# Mocking matplotlib if it's used in reports
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()
sys.modules['matplotlib.backends.backend_tkagg'] = MagicMock()
sys.modules['matplotlib.figure'] = MagicMock()

import customtkinter as ctk

class TestUIInterfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Prevent actual window creation but allow CTk widgets to be created
        cls.root = ctk.CTk()
        cls.root.withdraw()

    def test_dashboard(self):
        from ui.dashboard import DashboardView
        view = DashboardView(self.root, MagicMock())
        self.assertIsNotNone(view)

    def test_orders(self):
        from ui.orders import OrdersView
        view = OrdersView(self.root, MagicMock())
        self.assertIsNotNone(view)

    def test_expenses(self):
        from ui.expenses import ExpensesView
        view = ExpensesView(self.root, MagicMock())
        self.assertIsNotNone(view)

    def test_inventory(self):
        from ui.inventory import InventoryView
        view = InventoryView(self.root, MagicMock())
        self.assertIsNotNone(view)

    def test_catalog(self):
        from ui.catalog import CatalogView
        view = CatalogView(self.root, MagicMock())
        self.assertIsNotNone(view)

    def test_clients(self):
        from ui.clients import ClientsView
        view = ClientsView(self.root, MagicMock())
        self.assertIsNotNone(view)

    def test_reports(self):
        from ui.reports import ReportsView
        view = ReportsView(self.root, MagicMock())
        self.assertIsNotNone(view)

    def test_calendar(self):
        from ui.calendar import CalendarView
        view = CalendarView(self.root, MagicMock())
        self.assertIsNotNone(view)

    def test_settings(self):
        from ui.settings import SettingsView
        view = SettingsView(self.root, MagicMock())
        self.assertIsNotNone(view)

    def test_calculator(self):
        from ui.calculator import CalculatorWindow
        # CalculatorWindow is a Toplevel, so it creates a window
        win = CalculatorWindow(self.root)
        self.assertIsNotNone(win)
        win.destroy()

if __name__ == '__main__':
    unittest.main()
