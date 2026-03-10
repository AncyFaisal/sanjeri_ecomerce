# Design Document: COD Order Refund Fix

## Overview

This design addresses critical gaps in the order refund workflow by introducing a centralized, idempotent refund processing method in the Order model and updating the admin view to properly handle direct status changes to 'refunded'. The solution ensures that all refund paths (direct status change, return approval, and order cancellation) use consistent logic, preventing duplicate refunds while maintaining backward compatibility with existing flows.

The core design principle is idempotency: refund operations can be called multiple times safely without creating duplicate wallet credits. This is achieved through refund state tracking using the `refund_processed_at` timestamp and checking for existing COMPLETED refund transactions.

## Architecture

### Component Overview

The refund system consists of three main components:

1. **Order Model** (`sanjeri_app/models/order.py`)
   - Contains the new `process_refund()` method
   - Manages refund state tracking
   - Coordinates with Wallet and WalletTransaction models

2. **Admin View** (`sanjeri_app/views/admin_order_management.py`)
   - Handles status change requests from admin panel
   - Routes refund requests to appropriate methods
   - Provides user feedback on refund operations

3. **Wallet System** (`sanjeri_app/models/wallet.py`)
   - Wallet model stores user balance
   - WalletTransaction model tracks all wallet operations
   - Provides `mark_as_completed()` method for processing refunds

### Data Flow

```
Admin changes status to 'refunded'
    ↓
update_order_status() view
    ↓
Check if return_status == 'requested'
    ↓
    ├─ YES → approve_return() [existing flow]
    │         ↓
    │         process_refund() [new method]
    │
    └─ NO → process_refund() [new method]
            ↓
            Check if already refunded
            ↓
            ├─ YES → Return True (idempotent)
            │
            └─ NO → Calculate refund amount
                    ↓
                    Create COMPLETED WalletTransaction
                    ↓
                    Update Wallet.balance
                    ↓
                    Update User.wallet_balance
                    ↓
                    Set refund_processed_at timestamp
                    ↓
                    Update order status and payment_status
```

## Components and Interfaces

### Order.process_refund() Method

**Signature:**
```python
def process_refund(self, approved_by=None) -> bool
```

**Parameters:**
- `approved_by` (CustomUser, optional): The admin user who approved the refund. Used for audit trail in WalletTransaction.

**Returns:**
- `bool`: True if refund was processed or already processed, False if refund cannot be processed (e.g., payment was pending)

**Behavior:**

1. **Idempotency Check:**
   - Check if `refund_processed_at` is not None → return True
   - Check if COMPLETED refund transaction exists for this order → return True

2. **Payment Validation:**
   - Check if `payment_status` in ['completed', 'success', 'partially_paid']
   - If not → return False (no payment to refund)

3. **Refund Amount Calculation:**
   - If `payment_status` in ['completed', 'success']:
     - `refund_amount = total_amount`
   - If `payment_status` == 'partially_paid':
     - `refund_amount = wallet_amount_used + (amount paid online)`
   - Ensure `refund_amount > 0`

4. **Wallet Transaction Creation:**
   - Get or create user's Wallet
   - Create WalletTransaction:
     - `transaction_type='REFUND'`
     - `status='COMPLETED'`
     - `amount=refund_amount`
     - `order=self`
     - `admin_approved=True`
     - `approved_by=approved_by`
     - `reason=f"Refund for order #{order_number}"`

5. **Balance Updates:**
   - `wallet.balance += refund_amount`
   - `wallet.save(update_fields=['balance'])`
   - `user.wallet_balance = wallet.balance`
   - `user.save(update_fields=['wallet_balance'])`

6. **Order State Updates:**
   - `self.status = 'refunded'`
   - `self.payment_status = 'refunded'`
   - `self.refund_amount = refund_amount`
   - `self.refund_processed_at = timezone.now()`
   - `self.refund_to_wallet = True`
   - `self.save()`

7. **Error Handling:**
   - Wrap all operations in try-except
   - Log errors with traceback
   - Return False on exception

### Modified update_order_status() View

**Changes to Refunded Status Handling:**

```python
if new_status == 'refunded' and old_status != 'refunded':
    # Check if this is a return request approval
    if order.return_status == 'requested':
        # Use existing approve_return flow
        if order.approve_return(approved_by=request.user):
            messages.success(request, f"Return approved and ₹{order.total_amount} refunded to wallet.")
        else:
            messages.error(request, "Failed to process refund.")
    else:
        # Direct refund (no return request)
        if order.process_refund(approved_by=request.user):
            messages.success(request, f"Order refunded. ₹{order.refund_amount} credited to wallet.")
        else:
            messages.error(request, "Failed to process refund. Order may not have been paid.")
    
    return redirect('admin_order_detail', order_id=order_id)
```

### Modified approve_return() Method

**Integration with process_refund():**

The existing `approve_return()` method should be refactored to use `process_refund()` for the actual refund processing:

```python
def approve_return(self, approved_by):
    """Admin approves return and processes refund"""
    if self.return_status != 'requested':
        return False
    
    try:
        # Update return status first
        self.return_status = 'approved'
        self.return_approved_at = timezone.now()
        self.return_approved_by = approved_by
        self.save()
        
        # Delete any PENDING refund transaction (we'll create COMPLETED one)
        from .wallet import WalletTransaction
        WalletTransaction.objects.filter(
            order=self,
            transaction_type='REFUND',
            status='PENDING'
        ).delete()
        
        # Use centralized refund processing
        return self.process_refund(approved_by=approved_by)
        
    except Exception as e:
        print(f"Error approving return: {e}")
        import traceback
        traceback.print_exc()
        return False
```

### Backward Compatibility

**Existing Methods Preserved:**

1. **cancel_order()**: Remains unchanged. Already has proper refund logic.
2. **request_return()**: Remains unchanged. Creates PENDING transaction for admin approval.
3. **reject_return()**: Remains unchanged. Marks PENDING transaction as CANCELLED.

**Migration Path:**

No database migrations required. All new fields (`refund_processed_at`, `refund_amount`, `refund_to_wallet`) already exist in the Order model.

## Data Models

### Order Model Fields Used

**Existing Fields:**
- `status` (CharField): Order status, updated to 'refunded'
- `payment_status` (CharField): Payment status, updated to 'refunded'
- `payment_method` (CharField): Used to determine refund handling (cod, online, wallet, mixed)
- `total_amount` (DecimalField): Total order amount to refund
- `wallet_amount_used` (DecimalField): Amount paid from wallet
- `refund_amount` (DecimalField): Amount refunded (updated by process_refund)
- `refund_processed_at` (DateTimeField): Timestamp when refund was processed (idempotency check)
- `refund_to_wallet` (BooleanField): Flag indicating refund was sent to wallet
- `return_status` (CharField): Status of return request (requested, approved, rejected)
- `return_approved_by` (ForeignKey): Admin who approved the return
- `return_approved_at` (DateTimeField): When return was approved

**Idempotency Fields:**
- `refund_processed_at`: Primary idempotency check. If set, refund already processed.
- Existing COMPLETED WalletTransaction: Secondary check via query.

### WalletTransaction Model

**Fields Used:**
- `wallet` (ForeignKey): Link to user's wallet
- `amount` (DecimalField): Refund amount
- `transaction_type` (CharField): Set to 'REFUND'
- `status` (CharField): Set to 'COMPLETED'
- `order` (ForeignKey): Link to the order being refunded
- `reason` (TextField): Description of refund
- `admin_approved` (BooleanField): Set to True for admin-initiated refunds
- `approved_by` (ForeignKey): Admin user who approved the refund

### Wallet Model

**Fields Used:**
- `user` (OneToOneField): Link to user
- `balance` (DecimalField): Current wallet balance, incremented by refund amount

### CustomUser Model

**Fields Used:**
- `wallet_balance` (DecimalField): Cached wallet balance, synchronized with Wallet.balance

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Refund Status Updates

*For any* paid order, when process_refund is called successfully, both the order status and payment_status should be updated to 'refunded'.

**Validates: Requirements 1.1, 1.2**

### Property 2: Refund Amount Calculation

*For any* order, the refund amount should equal the amount the user actually paid:
- If payment_status is 'completed' or 'success', refund_amount equals total_amount
- If payment_status is 'partially_paid', refund_amount equals the sum of wallet_amount_used and online payment amount
- If payment_status is 'pending', no refund is processed (refund_amount remains 0)

**Validates: Requirements 1.3, 2.1, 2.3, 2.4**

### Property 3: Wallet Transaction Creation

*For any* paid order, when a refund is processed, a WalletTransaction should be created with transaction_type='REFUND', status='COMPLETED', and amount equal to the refund amount.

**Validates: Requirements 1.4, 4.4, 9.1, 9.2**

### Property 4: Wallet Balance Increase

*For any* paid order with initial wallet balance B, after processing a refund of amount R, the wallet balance should equal B + R.

**Validates: Requirements 1.5**

### Property 5: Wallet Balance Synchronization

*For any* order, after process_refund completes successfully, the user's wallet_balance field should equal the Wallet model's balance field.

**Validates: Requirements 1.6, 8.2, 8.3**

### Property 6: Idempotent Refund Processing

*For any* paid order, calling process_refund multiple times should produce the same result as calling it once:
- Only one COMPLETED refund WalletTransaction exists
- Wallet balance increases by refund amount only once
- refund_processed_at timestamp is set only once

**Validates: Requirements 3.1, 3.2, 4.7**

### Property 7: Unpaid Order Refund Rejection

*For any* order with payment_status='pending', calling process_refund should return False and should not create any WalletTransaction or modify wallet balance.

**Validates: Requirements 4.3**

### Property 8: Refund Timestamp Setting

*For any* paid order, after process_refund completes successfully, the refund_processed_at field should be set to a non-null timestamp.

**Validates: Requirements 4.6**

### Property 9: Transaction Audit Trail

*For any* refund processed by an admin user A, the created WalletTransaction should have:
- admin_approved=True
- approved_by=A
- order foreign key pointing to the refunded order

**Validates: Requirements 9.3, 9.4, 9.5**

### Property 10: Error Handling Return Value

*For any* order, if process_refund encounters an exception during execution, it should return False to indicate failure.

**Validates: Requirements 10.2**

## Error Handling

### Exception Handling Strategy

All refund operations are wrapped in try-except blocks to ensure graceful failure:

```python
def process_refund(self, approved_by=None):
    try:
        # Refund processing logic
        ...
        return True
    except Exception as e:
        print(f"Error processing refund for order {self.order_number}: {e}")
        import traceback
        traceback.print_exc()
        return False
```

### Error Scenarios

1. **Database Errors:**
   - Wallet or WalletTransaction creation fails
   - Order save fails
   - **Handling:** Log error, return False, no partial state changes

2. **Validation Errors:**
   - Order already refunded (idempotency check)
   - Payment status is 'pending' (no payment to refund)
   - **Handling:** Return True (idempotent) or False (invalid state), no error raised

3. **Concurrent Modifications:**
   - Multiple admins process refund simultaneously
   - **Handling:** Database-level uniqueness constraints prevent duplicate transactions, idempotency checks prevent duplicate refunds

4. **Missing Related Objects:**
   - User has no Wallet
   - **Handling:** Create Wallet using get_or_create()

### View-Level Error Handling

The `update_order_status` view catches exceptions and provides user-friendly feedback:

```python
try:
    if order.process_refund(approved_by=request.user):
        messages.success(request, f"Order refunded. ₹{order.refund_amount} credited to wallet.")
    else:
        messages.error(request, "Failed to process refund. Order may not have been paid.")
except Exception as e:
    messages.error(request, "An error occurred while processing the refund.")
    print(f"Refund error: {e}")
```

### Logging Strategy

All refund operations log key events:

1. **Success Logs:**
   - Refund amount and order number
   - Updated wallet balance
   - Transaction ID

2. **Failure Logs:**
   - Exception message and traceback
   - Order number and payment status
   - Current order state

3. **Idempotency Logs:**
   - When refund is skipped due to already being processed
   - Existing refund_processed_at timestamp

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests:**
- Specific examples of refund scenarios (COD delivered order, online paid order, mixed payment)
- Edge cases (unpaid orders, already refunded orders)
- Integration between Order, Wallet, and WalletTransaction models
- View-level behavior (success/error messages, redirects)

**Property-Based Tests:**
- Universal properties that hold for all valid inputs
- Randomized order generation with various payment states
- Idempotency verification across multiple refund attempts
- Balance calculation correctness across all payment scenarios

### Property-Based Testing Configuration

**Library:** Use `hypothesis` for Python property-based testing

**Test Configuration:**
- Minimum 100 iterations per property test
- Each test tagged with feature name and property number
- Tag format: `# Feature: cod-order-refund-fix, Property N: [property description]`

**Example Test Structure:**

```python
from hypothesis import given, strategies as st
import pytest

@given(
    payment_status=st.sampled_from(['completed', 'success']),
    total_amount=st.decimals(min_value=100, max_value=10000, places=2)
)
@pytest.mark.property_test
def test_refund_amount_calculation_for_paid_orders(payment_status, total_amount):
    """
    Feature: cod-order-refund-fix, Property 2: Refund Amount Calculation
    
    For any paid order, refund amount should equal total_amount
    """
    # Create order with given payment_status and total_amount
    order = create_test_order(
        payment_status=payment_status,
        total_amount=total_amount
    )
    
    # Process refund
    result = order.process_refund()
    
    # Verify refund amount equals total amount
    assert result is True
    assert order.refund_amount == total_amount
```

### Test Coverage Requirements

**Unit Tests Should Cover:**
1. Direct status change to 'refunded' via admin view
2. Return request approval flow
3. Order cancellation flow (existing behavior)
4. Unpaid order refund rejection
5. Already refunded order idempotency
6. Wallet balance synchronization
7. Error message display in admin view

**Property Tests Should Cover:**
1. All 10 correctness properties listed above
2. Randomized order generation with various:
   - Payment statuses (pending, completed, success, partially_paid)
   - Payment methods (cod, online, wallet, mixed)
   - Order amounts (100 to 10000)
   - Wallet usage scenarios (0 to full amount)

### Integration Testing

**Test Scenarios:**
1. End-to-end refund flow: Create order → Mark as delivered → Change status to refunded → Verify wallet credit
2. Return request flow: Create order → Deliver → Request return → Admin approve → Verify wallet credit
3. Cancellation flow: Create order → Cancel → Verify wallet credit (if paid)
4. Concurrent refund attempts: Multiple threads try to refund same order → Only one succeeds

### Manual Testing Checklist

1. ✓ Admin changes COD order (delivered) to 'refunded' → Wallet credited
2. ✓ Admin changes online order (paid) to 'refunded' → Wallet credited
3. ✓ Admin changes pending order to 'refunded' → No wallet credit, error message
4. ✓ Admin changes already refunded order to 'refunded' → No duplicate credit
5. ✓ User views order detail page → Sees 'Refunded' status
6. ✓ Admin approves return request → Wallet credited (existing flow)
7. ✓ User cancels paid order → Wallet credited (existing flow)
