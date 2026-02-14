document.addEventListener('DOMContentLoaded', function() {
    // Facility selection in booking process
    const facilityCards = document.querySelectorAll('.facility-card');
    if (facilityCards.length > 0) {
        facilityCards.forEach(card => {
            card.addEventListener('click', function() {
                // Remove active class from all cards
                facilityCards.forEach(c => c.classList.remove('active'));
                // Add active class to clicked card
                this.classList.add('active');
                
                // Get facility ID and update hidden input
                const facilityId = this.dataset.facilityId;
                const facilityInput = document.getElementById('facility-input');
                if (facilityInput) {
                    facilityInput.value = facilityId;
                }
                
                // Update facility name in confirmation
                const facilityName = this.querySelector('h3').textContent;
                const confirmFacility = document.getElementById('confirm-facility');
                if (confirmFacility) {
                    confirmFacility.textContent = facilityName;
                }
                
                // Update step indicators
                updateStepIndicator('step-1', 'completed');
                updateStepIndicator('step-2', 'active');
                
                // Show time selection, hide facility selection
                toggleVisibility('.facility-selection', false);
                toggleVisibility('.time-selection', true);
                
                // Load available slots via AJAX
                loadTimeSlots(facilityId);
            });
        });
    }
    
    // Time slot selection
    function setupTimeSlots() {
        const timeSlots = document.querySelectorAll('.time-slot');
        if (timeSlots.length > 0) {
            timeSlots.forEach(slot => {
                slot.addEventListener('click', function() {
                    // Remove selected class from all slots
                    timeSlots.forEach(s => s.classList.remove('selected'));
                    // Add selected class to clicked slot
                    this.classList.add('selected');
                    
                    // Get slot ID and update hidden input
                    const slotId = this.dataset.slotId;
                    const slotInput = document.getElementById('slot-input');
                    if (slotInput) {
                        slotInput.value = slotId;
                    }
                    
                    // Update confirmation details
                    const timeText = this.querySelector('.slot-time').textContent;
                    const confirmTime = document.getElementById('confirm-time');
                    if (confirmTime) {
                        confirmTime.textContent = timeText;
                    }
                    
                    // Update step indicators
                    updateStepIndicator('step-2', 'completed');
                    updateStepIndicator('step-3', 'active');
                    
                    // Show confirmation, hide time selection
                    toggleVisibility('.time-selection', false);
                    toggleVisibility('.booking-confirmation', true);
                });
            });
        }
    }
    
    // Function to load time slots via AJAX
    function loadTimeSlots(facilityId) {
        const slotsContainer = document.querySelector('.time-slots');
        if (!slotsContainer) return;
        
        slotsContainer.innerHTML = '<p>Loading available slots...</p>';
        
        fetch(`/api/slots?facility_id=${facilityId}`)
            .then(response => {
                // Check if the response is okay before parsing JSON
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Received data:", data); // Debug output
                
                if (data.error) {
                    slotsContainer.innerHTML = `<p class="text-danger">${data.error}</p>`;
                    return;
                }
                
                if (data.length === 0) {
                    slotsContainer.innerHTML = '<p>No available slots found.</p>';
                    return;
                }
                
                slotsContainer.innerHTML = '';
                data.forEach(slot => {
                    const slotElement = document.createElement('div');
                    slotElement.className = 'time-slot';
                    slotElement.dataset.slotId = slot.id;
                    slotElement.innerHTML = `
                        <span class="slot-time">${slot.start} - ${slot.end}</span>
                        <span class="slot-capacity">${slot.capacity} slots left</span>
                    `;
                    slotsContainer.appendChild(slotElement);
                });
                
                setupTimeSlots();
            })
            .catch(error => {
                console.error('Error loading slots:', error);
                slotsContainer.innerHTML = `<p class="text-danger">Error loading slots: ${error.message}</p>`;
            });
    }
    
    // Helper function to update step indicators
    function updateStepIndicator(stepId, status) {
        const step = document.getElementById(stepId);
        if (step) {
            step.className = 'step ' + status;
        }
    }
    
    // Helper function to toggle visibility
    function toggleVisibility(selector, visible) {
        const element = document.querySelector(selector);
        if (element) {
            if (visible) {
                element.classList.remove('hidden');
            } else {
                element.classList.add('hidden');
            }
        }
    }
    
    // Handle back buttons in booking flow
    const backButtons = document.querySelectorAll('.back-btn');
    if (backButtons.length > 0) {
        backButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const target = this.dataset.target;
                if (target === 'facility') {
                    // Back to facility selection
                    updateStepIndicator('step-1', 'active');
                    updateStepIndicator('step-2', '');
                    toggleVisibility('.facility-selection', true);
                    toggleVisibility('.time-selection', false);
                } else if (target === 'time') {
                    // Back to time selection
                    updateStepIndicator('step-2', 'active');
                    updateStepIndicator('step-3', '');
                    toggleVisibility('.time-selection', true);
                    toggleVisibility('.booking-confirmation', false);
                }
            });
        });
    }
    
    // Form validation
    const loginForm = document.querySelector('form[action*="login"]');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const userIdInput = this.querySelector('#user_id');
            const passwordInput = this.querySelector('#password');
            
            if (!userIdInput.value.trim()) {
                e.preventDefault();
                showInputError(userIdInput, 'User ID is required');
                return;
            }
            
            if (!passwordInput.value) {
                e.preventDefault();
                showInputError(passwordInput, 'Password is required');
                return;
            }
        });
    }
    
    // Function to show input errors
    function showInputError(input, message) {
        // Remove any existing error message
        const existingError = input.parentElement.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        // Add error class to input
        input.classList.add('error');
        
        // Create and append error message
        const errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        errorElement.textContent = message;
        input.parentElement.appendChild(errorElement);
        
        // Remove error after user starts typing
        input.addEventListener('input', function() {
            input.classList.remove('error');
            const error = input.parentElement.querySelector('.error-message');
            if (error) {
                error.remove();
            }
        }, { once: true });
    }
    
    // Modify booking functionality
    const modifyBookingCards = document.querySelectorAll('.booking-card .select-booking-btn');
    if (modifyBookingCards.length > 0) {
        modifyBookingCards.forEach(btn => {
            btn.addEventListener('click', function() {
                const card = this.closest('.booking-card');
                const bookingId = card.dataset.bookingId;
                const slotId = card.dataset.slotId;
                const facilityId = card.dataset.facilityId;
                const facilityName = card.querySelector('h3').textContent;
                
                const bookingIdInput = document.getElementById('booking-id-input');
                const confirmFacility = document.getElementById('confirm-facility');
                
                if (bookingIdInput) bookingIdInput.value = bookingId;
                if (confirmFacility) confirmFacility.textContent = facilityName;
                
                // Update steps
                updateStepIndicator('step-1', 'completed');
                updateStepIndicator('step-2', 'active');
                
                // Hide bookings list, show new slots
                toggleVisibility('.bookings-list', false);
                toggleVisibility('.new-slots-selection', true);
                
                // Load alternative slots
                loadAlternativeSlots(bookingId, slotId, facilityId);
            });
        });
    }
    
    // Function to load alternative slots for modification
    function loadAlternativeSlots(bookingId, currentSlotId, facilityId) {
        const slotsContainer = document.getElementById('new-time-slots');
        if (!slotsContainer) return;
        
        slotsContainer.innerHTML = '<p>Loading available slots...</p>';
        
        fetch(`/api/slots?facility_id=${facilityId}&booking_id=${bookingId}&current_slot_id=${currentSlotId}`)
            .then(response => {
                console.log("Response status:", response.status);
                return response.json();
            })
            .then(data => {
                console.log("Received data:", data);
                
                if (data.error) {
                    slotsContainer.innerHTML = `<p class="text-danger">${data.error}</p>`;
                    return;
                }
                
                if (data.length === 0) {
                    slotsContainer.innerHTML = '<p>No other available slots found for this facility.</p>';
                    return;
                }
                
                slotsContainer.innerHTML = '';
                data.forEach(slot => {
                    const slotElement = document.createElement('div');
                    slotElement.className = 'time-slot';
                    slotElement.dataset.slotId = slot.id;
                    slotElement.innerHTML = `
                        <span class="slot-time">${slot.start} - ${slot.end}</span>
                        <span class="slot-capacity">${slot.capacity} slots left</span>
                    `;
                    
                    slotElement.addEventListener('click', function() {
                        document.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
                        this.classList.add('selected');
                        
                        const newSlotId = this.dataset.slotId;
                        const timeText = this.querySelector('.slot-time').textContent;
                        
                        const newSlotIdInput = document.getElementById('new-slot-id-input');
                        const confirmNewTime = document.getElementById('confirm-new-time');
                        
                        if (newSlotIdInput) newSlotIdInput.value = newSlotId;
                        if (confirmNewTime) confirmNewTime.textContent = timeText;
                        
                        // Update steps
                        updateStepIndicator('step-2', 'completed');
                        updateStepIndicator('step-3', 'active');
                        
                        // Show confirmation
                        toggleVisibility('.new-slots-selection', false);
                        toggleVisibility('.modification-confirmation', true);
                    });
                    
                    slotsContainer.appendChild(slotElement);
                });
            })
            .catch(error => {
                console.error('Error loading slots:', error);
                slotsContainer.innerHTML = '<p class="text-danger">Error loading slots. Please try again.</p>';
            });
    }
    
    // Facility filter in modification page
    const facilityFilter = document.getElementById('facility-filter');
    if (facilityFilter) {
        facilityFilter.addEventListener('change', function() {
            const facilityId = this.value;
            document.querySelectorAll('.booking-item').forEach(item => {
                if (facilityId === '' || item.dataset.facilityId === facilityId) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
});
