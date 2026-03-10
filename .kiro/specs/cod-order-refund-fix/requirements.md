# Requirements Document: COD Order Refund Fix

## Introduction

This specification addresses critical issues in the Django e-commerce application's order refund workflow. Currently, when an admin marks a COD (Cash on Delivery) order as "Refunded" from the admin panel, the order status does not update on the user side, and the refunded amount is not credited to the user's wallet. This fix ensures proper refund processing for all payment types (COD, online, and mixed payments) while maintaining idempotency to prevent duplicate refunds.

## Glossary

- **Order**: A purchase transaction in the e-commerce system containing order items, payment information, and status tracking
- **COD**: Cash on Delivery - a payment method where the customer pays upon receiving the order
- **Wallet**: A user's digital balance stored in the system that can be used for purchases or receive refunds
- **WalletTransaction**: A record of money movement in/out of a user's wallet (deposits, withdrawals, refunds)
- **Payment_Status**: The current state of payment for an order (pending, completed, success, refunded, failed, partially_paid)
- **Order_Status**: The current state of an order (pending, confirmed, shipped, delivered, cancelled, refunded, return_requested)
- **Refund_Processing**: The act of crediting money back to a user's wallet after order cancellation or return
- **Idempotency**: A property ensuring that performing the same operation multiple times produces the same result as performing it once
- **Admin_Panel**: The administrative interface where staff can manage orders and update order statuses
- **Return_Request**: A formal request from a user to return a delivered order and receive a refund

## Requirements

### Requirement 1: Direct Refund Status Change

**User Story:** As an admin, I want to mark any order as "Refunded" directly from the admin panel, so that the user receives their money back in their wallet without requiring a return request flow.

#### Acceptance Criteria

1. WHEN an admin changes an order status to 'refunded' from the admin panel, THE System SHALL update the order status to 'refunded'
2. WHEN an admin changes an order status to 'refunded', THE System SHALL update the payment_status to 'refunded'
3. WHEN an admin changes an order status to 'refunded', THE System SHALL calculate the refund amount based on what the user actually paid
4. WHEN an admin changes an order status to 'refunded', THE System SHALL create a WalletTransaction with status='COMPLETED' and transaction_type='REFUND'
5. WHEN an admin changes an order status to 'refunded', THE System SHALL credit the user's wallet balance with the refund amount
6. WHEN an admin changes an order status to 'refunded', THE System SHALL update the user's wallet_balance field to match the wallet balance

### Requirement 2: Refund Amount Calculation

**User Story:** As a system, I want to calculate the correct refund amount based on payment history, so that users receive exactly what they paid.

#### Acceptance Criteria

1. WHEN calculating refund amount for an order with payment_status='completed' or 'success', THE System SHALL refund the total_amount
2. WHEN calculating refund amount for an order with payment_status='pending', THE System SHALL refund zero (no payment was made)
3. WHEN calculating refund amount for an order with payment_status='partially_paid', THE System SHALL refund only the amount that was actually paid
4. WHEN calculating refund amount for a mixed payment order, THE System SHALL refund the sum of wallet_amount_used and online payment amount
5. WHEN calculating refund amount, THE System SHALL include all components: subtotal minus discounts plus shipping plus tax

### Requirement 3: Idempotent Refund Processing

**User Story:** As a system, I want to prevent duplicate refunds when an order status is changed to 'refunded' multiple times, so that users don't receive money they shouldn't.

#### Acceptance Criteria

1. WHEN an order with status='refunded' is changed to 'refunded' again, THE System SHALL not create a new WalletTransaction
2. WHEN an order with status='refunded' is changed to 'refunded' again, THE System SHALL not modify the wallet balance
3. WHEN processing a refund, THE System SHALL check if a COMPLETED refund transaction already exists for the order
4. WHEN a COMPLETED refund transaction exists for an order, THE System SHALL skip refund processing
5. WHEN an order has refund_processed_at timestamp set, THE System SHALL not process another refund

### Requirement 4: Reusable Refund Method

**User Story:** As a developer, I want a centralized refund processing method in the Order model, so that all refund flows (direct status change, return approval, cancellation) use consistent logic.

#### Acceptance Criteria

1. THE Order_Model SHALL provide a method named 'process_refund' that accepts an optional 'approved_by' parameter
2. WHEN process_refund is called, THE System SHALL check if refund was already processed before proceeding
3. WHEN process_refund is called on an unpaid order, THE System SHALL return False and not create any transactions
4. WHEN process_refund is called on a paid order, THE System SHALL create a COMPLETED WalletTransaction
5. WHEN process_refund is called, THE System SHALL update the order's payment_status to 'refunded'
6. WHEN process_refund is called, THE System SHALL set the refund_processed_at timestamp
7. WHEN process_refund is called multiple times on the same order, THE System SHALL return True without creating duplicate transactions

### Requirement 5: Admin View Integration

**User Story:** As an admin, I want the order status update view to properly handle refund processing, so that changing status to 'refunded' triggers all necessary refund operations.

#### Acceptance Criteria

1. WHEN the update_order_status view receives a status change to 'refunded', THE System SHALL call the order's process_refund method
2. WHEN the update_order_status view processes a refund successfully, THE System SHALL display a success message showing the refund amount
3. WHEN the update_order_status view processes a refund that fails, THE System SHALL display an error message
4. WHEN the update_order_status view processes a refund for an order with a return request, THE System SHALL use the existing approve_return flow
5. WHEN the update_order_status view processes a refund for an order without a return request, THE System SHALL use the new process_refund method

### Requirement 6: Backward Compatibility

**User Story:** As a system, I want existing refund flows to continue working, so that return requests and order cancellations still process refunds correctly.

#### Acceptance Criteria

1. WHEN a user requests a return and admin approves it, THE System SHALL process the refund using the approve_return method
2. WHEN a user cancels an order, THE System SHALL process the refund using the cancel_order method
3. WHEN approve_return is called, THE System SHALL create a COMPLETED WalletTransaction and update wallet balance
4. WHEN cancel_order is called on a paid order, THE System SHALL create a COMPLETED WalletTransaction and update wallet balance
5. THE System SHALL maintain all existing behavior for return_status field updates

### Requirement 7: User-Side Order Status Visibility

**User Story:** As a user, I want to see the updated order status on my order detail page, so that I know when my order has been refunded.

#### Acceptance Criteria

1. WHEN an admin changes an order status to 'refunded', THE System SHALL persist the status change to the database
2. WHEN a user views their order detail page, THE System SHALL display the current order status from the database
3. WHEN an order status is 'refunded', THE User_Interface SHALL display "Refunded" as the order status
4. WHEN an order payment_status is 'refunded', THE User_Interface SHALL display "Refunded" as the payment status

### Requirement 8: Wallet Balance Synchronization

**User Story:** As a system, I want to keep the user's wallet_balance field synchronized with their Wallet model balance, so that wallet balance is consistent across the application.

#### Acceptance Criteria

1. WHEN a WalletTransaction is marked as COMPLETED, THE System SHALL update the Wallet model's balance field
2. WHEN the Wallet model's balance is updated, THE System SHALL update the user's wallet_balance field to match
3. WHEN process_refund completes successfully, THE System SHALL ensure user.wallet_balance equals wallet.balance
4. WHEN a refund is processed, THE System SHALL save the user model with the updated wallet_balance

### Requirement 9: Transaction Status Tracking

**User Story:** As a system, I want to track the status of refund transactions, so that admins can audit refund processing.

#### Acceptance Criteria

1. WHEN a refund is processed, THE System SHALL create a WalletTransaction with transaction_type='REFUND'
2. WHEN a refund is completed, THE WalletTransaction SHALL have status='COMPLETED'
3. WHEN a refund is processed by an admin, THE WalletTransaction SHALL have admin_approved=True
4. WHEN a refund is processed by an admin, THE WalletTransaction SHALL store the admin user in the approved_by field
5. WHEN a refund transaction is created, THE System SHALL link it to the order via the order foreign key

### Requirement 10: Error Handling and Logging

**User Story:** As a developer, I want comprehensive error handling and logging for refund operations, so that I can debug issues when they occur.

#### Acceptance Criteria

1. WHEN process_refund encounters an exception, THE System SHALL log the error with traceback information
2. WHEN process_refund encounters an exception, THE System SHALL return False to indicate failure
3. WHEN a refund is processed successfully, THE System SHALL log the refund amount and wallet balance
4. WHEN a refund is skipped due to idempotency, THE System SHALL log that the refund was already processed
5. WHEN update_order_status processes a refund, THE System SHALL catch exceptions and display user-friendly error messages
