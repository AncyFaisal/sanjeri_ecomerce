# management/commands/fix_order_totals.py
from django.core.management.base import BaseCommand
from sanjeri_app.models import Order

class Command(BaseCommand):
    help = 'Recalculate totals for all existing orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--order-id',
            type=int,
            help='Recalculate only a specific order ID',
        )

    def handle(self, *args, **options):
        if options['order_id']:
            orders = Order.objects.filter(id=options['order_id'])
        else:
            orders = Order.objects.all()
        
        count = 0
        for order in orders:
            old_total = order.total_amount
            order.calculate_totals()
            new_total = order.total_amount
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Order #{order.order_number}: ₹{old_total} → ₹{new_total}'
                )
            )
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully recalculated {count} orders!')
        )