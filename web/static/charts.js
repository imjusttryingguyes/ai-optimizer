// Utility functions for charts and UI

// Format currency
function formatCurrency(value) {
	return new Intl.NumberFormat('ru-RU', {
		style: 'currency',
		currency: 'RUB',
		maximumFractionDigits: 0
	}).format(value);
}

// Format number
function formatNumber(value) {
	return new Intl.NumberFormat('ru-RU').format(value);
}

// Get severity color
function getSeverityColor(severity) {
	if (severity >= 80) return '#DC3545';
	if (severity >= 60) return '#FFC107';
	if (severity >= 40) return '#17A2B8';
	return '#28A745';
}

// Get severity label
function getSeverityLabel(severity) {
	if (severity >= 80) return '🔥 Critical';
	if (severity >= 60) return '🔴 High';
	if (severity >= 40) return '⚠️ Medium';
	return 'ℹ️ Low';
}

// Tooltip configuration for charts
const chartTooltip = {
	titleFont: { size: 12 },
	bodyFont: { size: 11 },
	backgroundColor: 'rgba(0, 0, 0, 0.8)',
	padding: 10,
	displayColors: true,
	borderRadius: 4
};

// Responsive options for charts
const responsiveOptions = {
	responsive: true,
	maintainAspectRatio: true,
	plugins: {
		tooltip: chartTooltip,
		legend: {
			display: true,
			position: 'bottom',
			labels: {
				font: { size: 11 },
				padding: 15,
				usePointStyle: true
			}
		}
	}
};

// Load CSV export
function exportToCSV() {
	fetch('/api/insights-csv')
		.then(response => response.blob())
		.then(blob => {
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'insights_' + new Date().toISOString().split('T')[0] + '.csv';
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);
		});
}

// Auto-refresh dashboard every 5 minutes
setTimeout(function() {
	if (window.location.pathname === '/') {
		location.reload();
	}
}, 5 * 60 * 1000);
