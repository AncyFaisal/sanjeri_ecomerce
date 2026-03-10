# Implementation Plan: COD Order Refund Fix

## Overview

This implementation plan breaks down the refund workflow fix into discrete, testable steps. The approach is to first implement the core `process_refund()` method in the Order model with comprehensive error handling and idempotency checks, then integrate it into the admin view, and finally refactor the existing `approve_return()` method to use the new centralized logic. Each step includes property-based tests to validate correctness properties.

## Tasks

- [ ] 1. Implement Order.process_refund() method
  - [ ] 1.1 Create the process_refund method with idempotency checks
    - Implement method signature: `def process_refund(self, approved_by=None) -> bool`
    - Add idempotency checks: return True if `refund_processed_at` is set
    - Add idempotency check: return True if COMPLETED refund transaction exists
    - Add payment validation: return False if payment_status is 'pending'
    - _Requirements: 3.1, 3.2, 4.1, 4.2, 4.3_
  
  - [ ]* 1.2 Write property test for idempotent refund processing
    - **Property 6: Idempotent Refund Processing**
    - **Validates: Requirements 3.1, 3.2, 4.7**
  
  - [ ] 1.3 Implement refund amount calculation logic
    - Calculate refund_amount based on payment_status
    - Handle 'completed'/'success' status: refund_amount = total_amount
    - Handle 'partially_paid' status: refund_amount = wallet_amount_used + online_amount
    - Ensure refund_amount > 0 before proceeding
    - _Requirements: 1.3, 2.1, 2.3, 2.4_
  
  - [ ]* 1.4 Write property test for refund amount calculation
    - **Property 2: Refund Amount Calculation**
    - **Validates: Requirements 1.3, 2.1, 2.3, 2.4**
  
  - [ ] 1.5 Implement wallet transaction creation and balance updates
    - Get or create user's Wallet using `get_or_create()`
    - Create WalletTransaction with status='COMPLETED', type='REFUND'
    - Set admin_approved=True and approved_by field
    - Update wallet.balance by adding refund_amount
    - Update user.wallet_balance to match wallet.balance
    - _Requirements: 1.4, 1.5, 1.6, 9.3, 9.4, 9.5_
  
  - [ ]* 1.6 Write property test for wallet transaction creation
    - **Property 3: Wallet Transaction Creation**
    - **Validates: Requirements 1.4, 4.4, 9.1, 9.2**
  
  - [ ]* 1.7 Write property test for wallet balance increase
    - **Property 4: Wallet Balance Increase**
    - **Validates: Requirements 1.5**
  
  - [ ]* 1.8 Write property test for wallet balance synchronization
    - **Property 5: Wallet Balance Synchronization**
    - **Validates: Requirements 1.6, 8.2, 8.3**
  
  - [ ] 1.9 Implement order state updates
    - Set order.status = 'refunded'
    - Set order.payment_status = 'refunded'
    - Set order.refund_amount = refund_amount
    - Set order.refund_processed_at = timezone.now()
    - Set order.refund_to_wallet = True
    - Save order with all updated fields
    - _Requirements: 1.1, 1.2, 4.5, 4.6_
  
  - [ ]* 1.10 Write property test for refund status updates
    - **Property 1: Refund Status Updates**
    - **Validates: Requirements 1.1, 1.2**
  
  - [ ]* 1.11 Write property test for refund timestamp setting
    - **Property 8: Refund Timestamp Setting**
    - **Validates: Requirements 4.6**
  
  - [ ] 1.12 Add comprehensive error handling
    - Wrap all operations in try-except block
    - Log errors with traceback using print statements
    - Return False on any exception
    - Ensure no partial state changes on error
    - _Requirements: 10.1, 10.2_
  
  - [ ]* 1.13 Write property test for error handling
    - **Property 10: Error Handling Return Value**
    - **Validates: Requirements 10.2**
  
  - [ ]* 1.14 Write property test for unpaid order handling
    - **Property 7: Unpaid Order Refund Rejection**
    - **Validates: Requirements 4.3**
  
  - [ ]* 1.15 Write property test for transaction audit trail
    - **Property 9: Transaction Audit Trail**
    - **Validates: Requirements 9.3, 9.4, 9.5**

- [ ] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Update admin view to use process_refund()
  - [ ] 3.1 Modify update_order_status view for 'refunded' status
    - Add check: if `new_status == 'refunded' and old_status != 'refunded'`
    - Add routing logic: if `order.return_status == 'requested'`, call `approve_return()`
    - Add routing logic: else, call `process_refund(approved_by=request.user)`
    - Add success message with refund amount on successful refund
    - Add error message on failed refund
    - Return redirect to admin_order_detail after processing
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ]* 3.2 Write unit tests for admin view refund handling
    - Test direct status change to 'refunded' displays success message
    - Test failed refund displays error message
    - Test return request approval uses approve_return flow
    - _Requirements: 5.2, 5.3_

- [ ] 4. Refactor approve_return() to use process_refund()
  - [ ] 4.1 Update approve_return method implementation
    - Keep return_status validation check at the beginning
    - Update return_status to 'approved' and set timestamps
    - Delete any PENDING refund transactions for the order
    - Call `self.process_refund(approved_by=approved_by)` for actual refund
    - Return the result from process_refund()
    - Keep try-except error handling
    - _Requirements: 6.1, 6.3_
  
  - [ ]* 4.2 Write unit tests for approve_return integration
    - Test approve_return creates COMPLETED transaction (not PENDING)
    - Test approve_return updates wallet balance correctly
    - Test approve_return maintains return_status updates
    - _Requirements: 6.3_

- [ ] 5. Verify backward compatibility
  - [ ]* 5.1 Write integration tests for existing flows
    - Test return request flow: request → approve → verify wallet credit
    - Test cancellation flow: cancel paid order → verify wallet credit
    - Test cancellation flow: cancel unpaid order → verify no wallet credit
    - _Requirements: 6.2, 6.4_

- [ ] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- The implementation maintains backward compatibility with existing return and cancellation flows
- All refund operations are idempotent and safe to call multiple times
