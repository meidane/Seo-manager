"""نقشه‌ی URL حسابداری + API."""
from django.urls import path

from . import views

app_name = 'finance'

urlpatterns = [
    path('', views.FinanceDashboardView.as_view(), name='dashboard'),
    path('transactions/', views.TransactionListView.as_view(), name='transactions'),
    path('banks/', views.BankListView.as_view(), name='banks'),
    path('import/', views.ImportView.as_view(), name='import'),
    path('payroll/', views.PayrollListView.as_view(), name='payroll'),
    path('ledger/', views.LedgerView.as_view(), name='ledger'),
    path('invoices/', views.InvoiceListView.as_view(), name='invoices'),
    path('invoices/new/', views.InvoiceFormView.as_view(), name='invoice_new'),
    path('invoices/<int:pk>/', views.InvoiceFormView.as_view(), name='invoice_edit_page'),

    # API
    path('api/banks/', views.bank_create, name='bank_create'),
    path('api/banks/<int:pk>/', views.bank_edit, name='bank_edit'),
    path('api/categories/', views.category_create, name='category_create'),
    path('api/categories/<int:pk>/', views.category_delete, name='category_delete'),
    path('api/tx/<int:pk>/', views.tx_edit, name='tx_edit'),
    path('api/tx/bulk/', views.tx_bulk, name='tx_bulk'),
    path('api/import/preview/', views.import_preview, name='import_preview'),
    path('api/import/confirm/', views.import_confirm, name='import_confirm'),
    path('api/payroll/', views.payroll_create, name='payroll_create'),
    path('api/payroll/<int:pk>/', views.payroll_edit, name='payroll_edit'),
    path('api/invoices/', views.invoice_create, name='invoice_create'),
    path('api/invoices/<int:pk>/', views.invoice_edit, name='invoice_edit'),
]
