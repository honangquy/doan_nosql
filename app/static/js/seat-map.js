/**
 * Seat Map JavaScript - Sơ đồ ghế với màu sắc trạng thái
 */

class SeatMap {
    constructor(containerId, tripId) {
        this.container = document.getElementById(containerId);
        this.tripId = tripId;
        this.selectedSeats = new Set(); // Changed to support multiple seats
        this.maxSeats = 5; // Maximum 5 seats per booking
        this.seatsData = {};
        this.layoutInfo = {};
        
        this.init();
    }
    
    async init() {
        try {
            this.showLoading();
            await this.loadSeatsData();
            this.renderSeatMap();
            this.attachEventListeners();
        } catch (error) {
            this.showError('Không thể tải dữ liệu ghế: ' + error.message);
        }
    }
    
    showLoading() {
        this.container.innerHTML = `
            <div class="seat-map-loading">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Đang tải...</span>
                </div>
                <div>Đang tải sơ đồ ghế...</div>
            </div>
        `;
    }
    
    showError(message) {
        this.container.innerHTML = `
            <div class="seat-map-error">
                <i class="bi bi-exclamation-triangle-fill fs-1"></i>
                <div class="mt-2">${message}</div>
                <button class="btn btn-primary mt-3" onclick="location.reload()">
                    Tải lại
                </button>
            </div>
        `;
    }
    
    async loadSeatsData() {
        const response = await fetch(`/api/seats/${this.tripId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        if (data.status !== 'success') {
            throw new Error(data.error || 'Lỗi không xác định');
        }
        
        this.seatsData = data.seats;
        this.layoutInfo = data.layout_info;
        this.tripInfo = data.trip_info;
        
        console.log('Loaded seats data:', this.seatsData);
        console.log('Layout info:', this.layoutInfo);
    }
    
    renderSeatMap() {
        const floors = this.layoutInfo.floors || 1;
        
        let html = `
            <div class="seat-map-container">
                ${this.renderLegend()}
                ${this.renderLayoutInfo()}
                <div class="bus-layout">
        `;
        
        if (floors === 1) {
            html += this.renderSingleFloor();
        } else {
            html += this.renderMultipleFloors();
        }
        
        html += `
                </div>
                ${this.renderSelectedSeatInfo()}
            </div>
        `;
        
        this.container.innerHTML = html;
    }
    
    renderLegend() {
        return `
            <div class="seat-legend">
                <div class="legend-item">
                    <div class="legend-color legend-available"></div>
                    <span>Trống</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color legend-occupied"></div>
                    <span>Đã đặt</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color legend-selected"></div>
                    <span>Đang chọn</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color legend-unavailable"></div>
                    <span>Không khả dụng</span>
                </div>
            </div>
        `;
    }
    
    renderLayoutInfo() {
        return `
            <div class="text-center mb-3">
                <h5 class="mb-1">${this.layoutInfo.name || 'Sơ đồ ghế'}</h5>
                <small class="text-muted">
                    ${this.layoutInfo.total_seats} ghế • ${this.layoutInfo.floors} tầng
                </small>
            </div>
        `;
    }
    
    renderSingleFloor() {
        // For single floor, get all seats regardless of prefix
        const allSeats = Object.keys(this.seatsData).sort();
        return `
            <div class="floor-section">
                <div class="floor-title">Sơ đồ ghế</div>
                ${this.renderSeatsInRows(allSeats)}
            </div>
        `;
    }
    
    renderMultipleFloors() {
        let html = '';
        for (let floor = 1; floor <= this.layoutInfo.floors; floor++) {
            const floorSeats = this.getSeatsForFloor(floor);
            html += `
                <div class="floor-section">
                    <div class="floor-title">Tầng ${floor}</div>
                    ${this.renderFloorSeats(floorSeats, floor)}
                </div>
            `;
        }
        return html;
    }
    
    renderFloorSeats(seats, floor) {
        // Get seats for this floor
        const seatNumbers = Object.keys(this.seatsData)
            .filter(seatNum => {
                // For 2-floor vehicles: A=floor1, B=floor2
                // For 1-floor vehicles: any prefix
                if (this.layoutInfo.floors === 1) {
                    return true; // All seats for single floor
                } else {
                    const seatFloor = seatNum.charAt(0) === 'A' ? 1 : 2;
                    return seatFloor === floor;
                }
            })
            .sort();
        
        return this.renderSeatsInRows(seatNumbers);
    }
    
    renderSeat(seatNumber) {
        const seatInfo = this.seatsData[seatNumber];
        if (!seatInfo) return '';
        
        const statusClass = `seat-${seatInfo.status}`;
        const typeClass = seatInfo.seatType ? `seat-${seatInfo.seatType.toLowerCase()}` : '';
        const isClickable = seatInfo.status === 'available';
        
        return `
            <div class="seat ${statusClass} ${typeClass}" 
                 data-seat="${seatNumber}"
                 data-clickable="${isClickable}"
                 title="${this.getSeatTooltip(seatNumber, seatInfo)}">
                ${seatNumber}
            </div>
        `;
    }
    
    getSeatTooltip(seatNumber, seatInfo) {
        if (seatInfo.status === 'occupied') {
            return `${seatNumber} - Đã đặt\\nKhách: ${seatInfo.customerName || 'N/A'}\\nSĐT: ${seatInfo.customerPhone || 'N/A'}\\nNgày đặt: ${seatInfo.bookingDate || 'N/A'}`;
        } else if (seatInfo.status === 'available') {
            return `${seatNumber} - Ghế trống\\nLoại: ${seatInfo.seatType || 'Ghế thường'}`;
        } else {
            return `${seatNumber} - Không khả dụng`;
        }
    }
    
    groupSeatsByRow() {
        const grouped = {};
        
        for (const seatNumber in this.seatsData) {
            const row = seatNumber.charAt(0); // A, B, C, etc.
            if (!grouped[row]) {
                grouped[row] = [];
            }
            grouped[row].push(seatNumber);
        }
        
        // Sort seats in each row
        for (const row in grouped) {
            grouped[row].sort((a, b) => {
                const numA = parseInt(a.slice(1));
                const numB = parseInt(b.slice(1));
                return numA - numB;
            });
        }
        
        return grouped;
    }
    
    getSeatsForFloor(floor) {
        const floorSeats = {};
        
        for (const seatNumber in this.seatsData) {
            const seatInfo = this.seatsData[seatNumber];
            if (seatInfo.floor === floor) {
                const row = seatNumber.charAt(0);
                if (!floorSeats[row]) {
                    floorSeats[row] = [];
                }
                floorSeats[row].push(seatNumber);
            }
        }
        
        // Sort seats in each row
        for (const row in floorSeats) {
            floorSeats[row].sort((a, b) => {
                const numA = parseInt(a.slice(1));
                const numB = parseInt(b.slice(1));
                return numA - numB;
            });
        }
        
        return floorSeats;
    }
    
    groupSeatsByFloorRow(seats, floor) {
        const floorRows = {};
        
        // Group seats by row letter for this floor
        for (const seatNumber in this.seatsData) {
            const seatInfo = this.seatsData[seatNumber];
            
            // Determine floor based on seat prefix (A/B for floor 1/2)
            const seatFloor = seatNumber.charAt(0) === 'A' ? 1 : 2;
            
            if (seatFloor === floor) {
                const rowLetter = seatNumber.charAt(0);
                if (!floorRows[rowLetter]) {
                    floorRows[rowLetter] = [];
                }
                floorRows[rowLetter].push(seatNumber);
            }
        }
        
        // Sort seats in each row
        for (const rowLetter in floorRows) {
            floorRows[rowLetter].sort((a, b) => {
                const numA = parseInt(a.slice(1));
                const numB = parseInt(b.slice(1));
                return numA - numB;
            });
        }
        
        return floorRows;
    }
    
    renderSeatsInRows(seatNumbers) {
        let html = '';
        
        // Group seats into rows of 4
        for (let i = 0; i < seatNumbers.length; i += 4) {
            html += `<div class="seats-row">`;
            
            // Render 4 seats per row
            for (let j = 0; j < 4; j++) {
                const seatIndex = i + j;
                if (seatIndex < seatNumbers.length) {
                    const seatNumber = seatNumbers[seatIndex];
                    html += this.renderSeat(seatNumber);
                } else {
                    // Empty slot for grid alignment
                    html += `<div class="seat-placeholder"></div>`;
                }
            }
            
            html += `</div>`;
        }
        
        return html;
    }
    
    renderSelectedSeatInfo() {
        return `
            <div id="selected-seat-info" class="mt-3" style="display: none;">
                <div class="alert alert-info">
                    <strong>Ghế đã chọn: <span id="selected-seat-number"></span></strong>
                    <div id="selected-seat-details"></div>
                </div>
            </div>
        `;
    }
    
    attachEventListeners() {
        // Seat selection
        this.container.addEventListener('click', (e) => {
            if (e.target.classList.contains('seat') && e.target.dataset.clickable === 'true') {
                this.selectSeat(e.target.dataset.seat);
            }
        });
        
        // Tooltip functionality
        this.container.addEventListener('mouseenter', (e) => {
            if (e.target.classList.contains('seat')) {
                this.showTooltip(e.target);
            }
        }, true);
        
        this.container.addEventListener('mouseleave', (e) => {
            if (e.target.classList.contains('seat')) {
                this.hideTooltip();
            }
        }, true);
    }
    
    selectSeat(seatNumber) {
        const seatElement = this.container.querySelector(`[data-seat="${seatNumber}"]`);
        if (!seatElement) return;
        
        // Check if seat is already selected
        if (this.selectedSeats.has(seatNumber)) {
            // Unselect seat
            this.selectedSeats.delete(seatNumber);
            seatElement.classList.remove('seat-selected');
            seatElement.classList.add('seat-available');
        } else {
            // Check seat limit
            if (this.selectedSeats.size >= this.maxSeats) {
                alert(`Bạn chỉ có thể chọn tối đa ${this.maxSeats} ghế cho một đơn hàng.`);
                return;
            }
            
            // Select new seat
            this.selectedSeats.add(seatNumber);
            seatElement.classList.remove('seat-available');
            seatElement.classList.add('seat-selected');
        }
        
        this.updateSelectedSeatInfo();
        
        // Trigger custom event for external handling
        this.container.dispatchEvent(new CustomEvent('seatSelected', {
            detail: {
                selectedSeats: Array.from(this.selectedSeats),
                seatCount: this.selectedSeats.size
            }
        }));
    }
    
    updateSelectedSeatInfo() {
        const infoDiv = document.getElementById('selected-seat-info');
        const numberSpan = document.getElementById('selected-seat-number');
        const detailsDiv = document.getElementById('selected-seat-details');
        
        if (this.selectedSeats.size > 0 && infoDiv) {
            const seatNumbers = Array.from(this.selectedSeats).sort();
            numberSpan.textContent = seatNumbers.join(', ');
            
            const seatCount = this.selectedSeats.size;
            const remaining = this.maxSeats - seatCount;
            
            detailsDiv.innerHTML = `
                <small>
                    Số ghế đã chọn: ${seatCount}/${this.maxSeats}<br>
                    ${remaining > 0 ? `Có thể chọn thêm: ${remaining} ghế` : 'Đã đạt giới hạn tối đa'}
                </small>
            `;
            infoDiv.style.display = 'block';
        } else if (infoDiv) {
            infoDiv.style.display = 'none';
        }
        
        // Update booking form
        this.updateBookingForm();
    }
    
    showTooltip(element) {
        this.hideTooltip(); // Remove existing tooltip
        
        const tooltip = document.createElement('div');
        tooltip.className = 'seat-tooltip';
        tooltip.textContent = element.title;
        tooltip.id = 'seat-tooltip';
        
        document.body.appendChild(tooltip);
        
        const rect = element.getBoundingClientRect();
        tooltip.style.left = (rect.left + rect.width / 2) + 'px';
        tooltip.style.top = (rect.top - 10) + 'px';
    }
    
    hideTooltip() {
        const tooltip = document.getElementById('seat-tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }
    
    getSelectedSeats() {
        return Array.from(this.selectedSeats);
    }
    
    updateBookingForm() {
        // Update hidden form fields for selected seats
        const seatsInput = document.getElementById('selected-seats-input');
        const seatCountSpan = document.getElementById('seat-count-display');
        const totalPriceSpan = document.getElementById('total-price-display');
        
        if (seatsInput) {
            seatsInput.value = Array.from(this.selectedSeats).join(',');
        }
        
        if (seatCountSpan) {
            seatCountSpan.textContent = this.selectedSeats.size;
        }
        
        // Update total price calculation
        if (totalPriceSpan) {
            const basePrice = parseInt(document.querySelector('[data-base-price]')?.dataset.basePrice || 0);
            const serviceFee = 15000;
            const totalPrice = (basePrice + serviceFee) * this.selectedSeats.size;
            totalPriceSpan.textContent = totalPrice.toLocaleString('vi-VN') + 'đ';
        }
        
        // Enable/disable booking button
        const bookingBtn = document.getElementById('booking-submit-btn');
        if (bookingBtn) {
            bookingBtn.disabled = this.selectedSeats.size === 0;
            bookingBtn.textContent = this.selectedSeats.size > 0 
                ? `Đặt ${this.selectedSeats.size} vé` 
                : 'Chọn ghế để đặt vé';
        }
    }
    
    refresh() {
        this.init();
    }
}

// Global function to initialize seat map
window.initSeatMap = function(containerId, tripId) {
    return new SeatMap(containerId, tripId);
};