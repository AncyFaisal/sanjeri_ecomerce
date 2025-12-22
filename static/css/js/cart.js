// // Real-time cart functionality
// class CartManager {
//     constructor() {
//         this.init();
//     }

//     init() {
//         this.bindEvents();
//         this.updateCartBadge();
//     }

//     bindEvents() {
//         // Add to cart buttons
//         document.querySelectorAll('.add-to-cart-btn').forEach(btn => {
//             btn.addEventListener('click', (e) => this.handleAddToCart(e));
//         });
//     }

//     async handleAddToCart(event) {
//         const btn = event.target.closest('.add-to-cart-btn');
//         const variantId = btn.dataset.variantId;
        
//         if (!variantId) {
//             this.showMessage('Invalid product variant', 'error');
//             return;
//         }

//         btn.disabled = true;
//         const originalText = btn.innerHTML;
//         btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';

//         try {
//             const response = await this.addToCart(variantId);
            
//             if (response.success) {
//                 this.showMessage(response.message, 'success');
//                 this.updateCartBadge(response.cart_total_items);
                
//                 // Update any quantity displays
//                 this.updateCartUI(response);
//             } else {
//                 this.showMessage(response.message, 'error');
//             }
//         } catch (error) {
//             console.error('Add to cart error:', error);
//             this.showMessage('Error adding product to cart', 'error');
//         } finally {
//             btn.disabled = false;
//             btn.innerHTML = originalText;
//         }
//     }

//     async addToCart(variantId, quantity = 1) {
//         const formData = new FormData();
//         formData.append('quantity', quantity);
//         formData.append('csrfmiddlewaretoken', this.getCSRFToken());

//         const response = await fetch(`/cart/add/${variantId}/`, {
//             method: 'POST',
//             headers: {
//                 'X-Requested-With': 'XMLHttpRequest',
//             },
//             body: formData
//         });

//         return await response.json();
//     }

//     updateCartBadge(count = null) {
//         const badges = document.querySelectorAll('.cart-count, .cart-badge');
        
//         if (count !== null) {
//             badges.forEach(badge => {
//                 badge.textContent = count;
//                 badge.style.display = count > 0 ? 'inline' : 'none';
//             });
//         } else {
//             // Fetch current count
//             fetch('/cart/count/')
//                 .then(response => response.json())
//                 .then(data => {
//                     badges.forEach(badge => {
//                         badge.textContent = data.count;
//                         badge.style.display = data.count > 0 ? 'inline' : 'none';
//                     });
//                 })
//                 .catch(error => console.error('Error updating cart badge:', error));
//         }
//     }

//     updateCartUI(data) {
//         // Update any specific UI elements based on the response
//         if (data.item_quantity) {
//             const quantityEl = document.querySelector(`[data-variant-id="${data.variant_id}"] .quantity-display`);
//             if (quantityEl) {
//                 quantityEl.textContent = data.item_quantity;
//             }
//         }
//     }

//     getCSRFToken() {
//         return document.querySelector('[name=csrfmiddlewaretoken]').value;
//     }

//     showMessage(message, type = 'info') {
//         // Use your preferred notification system
//         const alertClass = {
//             'success': 'alert-success',
//             'error': 'alert-danger',
//             'warning': 'alert-warning',
//             'info': 'alert-info'
//         }[type] || 'alert-info';

//         // Create toast notification
//         const toast = document.createElement('div');
//         toast.className = `alert ${alertClass} alert-dismissible fade show`;
//         toast.innerHTML = `
//             ${message}
//             <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
//         `;
        
//         const container = document.querySelector('.toast-container') || this.createToastContainer();
//         container.appendChild(toast);
        
//         // Auto remove after 5 seconds
//         setTimeout(() => {
//             if (toast.parentNode) {
//                 toast.remove();
//             }
//         }, 5000);
//     }

//     createToastContainer() {
//         const container = document.createElement('div');
//         container.className = 'toast-container position-fixed top-0 end-0 p-3';
//         container.style.zIndex = '9999';
//         document.body.appendChild(container);
//         return container;
//     }
// }

// // Initialize cart manager when DOM is loaded
// document.addEventListener('DOMContentLoaded', function() {
//     window.cartManager = new CartManager();
// });