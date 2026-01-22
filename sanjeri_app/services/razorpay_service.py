# sanjeri_app/services/razorpay_service.py
import razorpay
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class RazorpayService:
    """Service to handle all Razorpay operations"""
    
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    
    def create_order(self, amount_in_rupees, currency='INR', notes=None):
        """Create Razorpay order"""
        try:
            amount_paise = int(amount_in_rupees * 100)
            
            order_data = {
                'amount': amount_paise,
                'currency': currency,
                'payment_capture': '1',  # Auto-capture
            }
            
            if notes:
                order_data['notes'] = notes
            
            logger.info(f"Creating Razorpay order: {amount_paise} paise")
            razorpay_order = self.client.order.create(order_data)
            logger.info(f"Order created: {razorpay_order['id']}")
            
            return {
                'success': True,
                'order_id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'created_at': razorpay_order.get('created_at'),
                'order_data': razorpay_order
            }
            
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment_signature(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """Verify payment signature"""
        try:
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            self.client.utility.verify_payment_signature(params_dict)
            return True
            
        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Signature verification failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    def fetch_payment(self, payment_id):
        """Fetch payment details from Razorpay"""
        try:
            payment = self.client.payment.fetch(payment_id)
            return payment
        except Exception as e:
            logger.error(f"Failed to fetch payment: {e}")
            return None