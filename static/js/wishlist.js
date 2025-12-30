// static/js/wishlist.js
class WishlistManager {
    constructor() {
        this.csrfToken = this.getCookie('csrftoken');
        this.initialize();
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    showNotification(message, type = 'info') {
        // Create notification if it doesn't exist
        let notification = document.getElementById('global-notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'global-notification';
            notification.className = 'notification';
            document.body.appendChild(notification);
        }

        notification.textContent = message;
        notification.className = `notification ${type} show`;
        
        setTimeout(() => {
            notification.classList.remove('show');
        }, 3000);
    }

    updateWishlistBadge(count) {
        // Update all wishlist badges in the header
        const badges = document.querySelectorAll('.wishlist-badge, .cart-count');
        badges.forEach(badge => {
            const parentLink = badge.closest('a');
            if (parentLink && parentLink.href.includes('wishlist')) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'flex' : 'none';
            }
        });
    }

    async addToWishlist(productId, button) {
        if (!button) return;
        
        const heartIcon = button.querySelector('i');
        const originalClass = heartIcon.className;
        
        // Show loading state
        heartIcon.className = 'fas fa-spinner fa-spin';
        button.disabled = true;
        
        try {
            const response = await fetch(`/wishlist/add/${productId}/`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.csrfToken,
                },
            });

            const data = await response.json();
            
            if (data.success) {
                // Update wishlist badge
                this.updateWishlistBadge(data.wishlist_total_items || data.wishlist_count);
                
                // Update button state
                heartIcon.className = 'fas fa-heart text-danger';
                button.classList.add('in-wishlist');
                button.title = 'Remove from Wishlist';
                
                this.showNotification('Added to wishlist!', 'success');
            } else {
                heartIcon.className = originalClass;
                this.showNotification(data.message || 'Error', 'error');
            }
        } catch (error) {
            console.error('Wishlist error:', error);
            
            if (error.status === 403 || error.status === 401) {
                this.showNotification('Please login to use wishlist', 'error');
                setTimeout(() => {
                    window.location.href = `/user-login/?next=${encodeURIComponent(window.location.pathname)}`;
                }, 1500);
            } else {
                heartIcon.className = originalClass;
                this.showNotification('Network error. Please try again.', 'error');
            }
        } finally {
            button.disabled = false;
        }
    }

    async removeFromWishlist(productId, button) {
        if (!button) return;
        
        const heartIcon = button.querySelector('i');
        const originalClass = heartIcon.className;
        
        // Show loading state
        heartIcon.className = 'fas fa-spinner fa-spin';
        button.disabled = true;
        
        try {
            // First find the wishlist item ID
            const itemResponse = await fetch(`/wishlist/get-item-id/${productId}/`);
            const itemData = await itemResponse.json();
            
            if (itemData.item_id) {
                const response = await fetch(`/wishlist/remove/${itemData.item_id}/`, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': this.csrfToken,
                    },
                });

                const data = await response.json();
                
                if (data.success) {
                    // Update wishlist badge
                    this.updateWishlistBadge(data.wishlist_total_items);
                    
                    // Update button state
                    heartIcon.className = 'far fa-heart';
                    button.classList.remove('in-wishlist');
                    button.title = 'Add to Wishlist';
                    
                    this.showNotification('Removed from wishlist', 'success');
                }
            }
        } catch (error) {
            console.error('Remove from wishlist error:', error);
            heartIcon.className = originalClass;
            this.showNotification('Error removing item', 'error');
        } finally {
            button.disabled = false;
        }
    }

    async toggleWishlist(productId, button) {
        const isInWishlist = button.classList.contains('in-wishlist');
        
        if (isInWishlist) {
            await this.removeFromWishlist(productId, button);
        } else {
            await this.addToWishlist(productId, button);
        }
    }

    initialize() {
        // Handle wishlist button clicks
        document.addEventListener('click', (e) => {
            const wishlistBtn = e.target.closest('.add-to-wishlist-btn');
            if (wishlistBtn) {
                e.preventDefault();
                const productId = wishlistBtn.getAttribute('data-product-id');
                if (productId) {
                    this.toggleWishlist(productId, wishlistBtn);
                }
            }
        });

        // Initialize current wishlist count
        this.initializeWishlistCount();
    }

    async initializeWishlistCount() {
        try {
            const response = await fetch('/wishlist/count/');
            if (response.ok) {
                const data = await response.json();
                this.updateWishlistBadge(data.count || 0);
            }
        } catch (error) {
            console.log('Could not fetch initial wishlist count');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.wishlistManager = new WishlistManager();
});