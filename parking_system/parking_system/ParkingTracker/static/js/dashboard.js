document.addEventListener('DOMContentLoaded', () => {
  const chartCanvas = document.getElementById('occupancyTrendChart');
  if (chartCanvas && window.Chart) {
    new Chart(chartCanvas, {
      type: 'line',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [
          {
            label: 'Predicted Occupancy',
            data: [68, 76, 71, 75, 83, 80, 78],
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.2)',
            fill: true,
            tension: 0.35,
            pointRadius: 4,
          },
          {
            label: 'Available Slots',
            data: [32, 24, 29, 25, 17, 20, 22],
            borderColor: '#22c55e',
            backgroundColor: 'rgba(34, 197, 94, 0.2)',
            fill: true,
            tension: 0.35,
            pointRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          x: {
            grid: { color: 'rgba(148, 163, 184, 0.1)' },
            ticks: { color: '#cbd5e1' },
          },
          y: {
            beginAtZero: true,
            max: 100,
            grid: { color: 'rgba(148, 163, 184, 0.1)' },
            ticks: { color: '#cbd5e1' },
          },
        },
        plugins: {
          legend: {
            labels: { color: '#cbd5e1' },
          },
        },
      },
    });
  }
});
