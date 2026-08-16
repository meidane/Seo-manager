from django.contrib import admin

from .models import (BankAccount, Category, Invoice, InvoiceLine, Payroll,
                     PayrollItem, Transaction)


@admin.register(BankAccount)
class BankAdmin(admin.ModelAdmin):
    list_display = ('name', 'bank', 'initial_balance', 'is_active')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_salary', 'order')


@admin.register(Transaction)
class TxAdmin(admin.ModelAdmin):
    list_display = ('date', 'description', 'deposit', 'withdrawal', 'bank_account', 'project', 'category')
    list_filter = ('bank_account', 'category')
    date_hierarchy = 'date'


class ItemInline(admin.TabularInline):
    model = PayrollItem
    extra = 1


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('colleague', 'year', 'month', 'paid_amount')
    inlines = [ItemInline]


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'issue_date', 'project', 'due_date')
    list_filter = ('project',)
    date_hierarchy = 'issue_date'
    inlines = [InvoiceLineInline]
