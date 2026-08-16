/**
 * Gestor interactivo de gráficos con Chart.js compatible con Modo Oscuro y HTMX
 */

class DashboardChartsManager {
  constructor() {
    this.chartIngresosGastos = null;
    this.chartAhorroAcumulado = null;
    this.chartDistribucion = null;
  }

  isDarkMode() {
    return document.documentElement.classList.contains('dark');
  }

  getThemeColors() {
    const isDark = this.isDarkMode();
    return {
      textColor: isDark ? '#94A3B8' : '#64748B',
      gridColor: isDark ? 'rgba(51, 65, 85, 0.4)' : 'rgba(226, 232, 240, 0.8)',
      tooltipBg: isDark ? '#0F172A' : '#FFFFFF',
      tooltipText: isDark ? '#F8FAFC' : '#0F172A',
      tooltipBorder: isDark ? '#1E293B' : '#E2E8F0',
      cyan500: '#3BB8DB',
      cyan600: '#2C92B8',
      cyan300: '#53EAFD',
      cyan800: '#015F78',
      gastosColor: '#EF4444',
      gastosBg: 'rgba(239, 68, 68, 0.85)',
      ingresosBg: 'rgba(59, 184, 219, 0.85)',
    };
  }

  init(data) {
    if (!data) return;
    this.renderChartIngresosGastos(data);
    this.renderChartAhorroAcumulado(data);
    this.renderChartDistribucion(data);
  }

  renderChartIngresosGastos(data) {
    const ctx = document.getElementById('chartIngresosGastos');
    if (!ctx) return;

    if (this.chartIngresosGastos) {
      this.chartIngresosGastos.destroy();
    }

    const colors = this.getThemeColors();

    this.chartIngresosGastos = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.meses,
        datasets: [
          {
            label: 'Ingresos (€)',
            data: data.ingresos,
            backgroundColor: colors.ingresosBg,
            borderRadius: 6,
            barPercentage: 0.7,
            categoryPercentage: 0.6,
          },
          {
            label: 'Gastos (€)',
            data: data.gastos,
            backgroundColor: colors.gastosBg,
            borderRadius: 6,
            barPercentage: 0.7,
            categoryPercentage: 0.6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              color: colors.textColor,
              usePointStyle: true,
              pointStyle: 'circle',
              boxWidth: 8,
              font: { size: 12, family: 'system-ui' },
            },
          },
          tooltip: {
            backgroundColor: colors.tooltipBg,
            titleColor: colors.tooltipText,
            bodyColor: colors.tooltipText,
            borderColor: colors.tooltipBorder,
            borderWidth: 1,
            padding: 10,
            boxPadding: 4,
            callbacks: {
              label: function (context) {
                return ` ${context.dataset.label}: ${context.raw.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: colors.textColor, font: { size: 11 } },
          },
          y: {
            grid: { color: colors.gridColor },
            ticks: {
              color: colors.textColor,
              font: { size: 11 },
              callback: (value) => `${value} €`,
            },
          },
        },
      },
    });
  }

  renderChartAhorroAcumulado(data) {
    const ctx = document.getElementById('chartAhorroAcumulado');
    if (!ctx) return;

    if (this.chartAhorroAcumulado) {
      this.chartAhorroAcumulado.destroy();
    }

    const colors = this.getThemeColors();
    const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 240);
    gradient.addColorStop(0, 'rgba(59, 184, 219, 0.45)');
    gradient.addColorStop(1, 'rgba(59, 184, 219, 0.0)');

    this.chartAhorroAcumulado = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.meses,
        datasets: [
          {
            label: 'Ahorro Acumulado (€)',
            data: data.ahorro_acumulado,
            borderColor: colors.cyan500,
            borderWidth: 2.5,
            fill: true,
            backgroundColor: gradient,
            tension: 0.35,
            pointBackgroundColor: colors.cyan500,
            pointBorderColor: '#FFFFFF',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: colors.tooltipBg,
            titleColor: colors.tooltipText,
            bodyColor: colors.tooltipText,
            borderColor: colors.tooltipBorder,
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: (context) => ` Ahorro Acumulado: ${context.raw.toLocaleString('es-ES', { minimumFractionDigits: 2 })} €`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: colors.textColor, font: { size: 11 } },
          },
          y: {
            grid: { color: colors.gridColor },
            ticks: {
              color: colors.textColor,
              font: { size: 11 },
              callback: (value) => `${value} €`,
            },
          },
        },
      },
    });
  }

  renderChartDistribucion(data) {
    const ctx = document.getElementById('chartDistribucion');
    if (!ctx) return;

    if (this.chartDistribucion) {
      this.chartDistribucion.destroy();
    }

    const colors = this.getThemeColors();
    const distData = data.distribucion;

    if (!distData.data || distData.data.length === 0) {
      // Estado sin datos
      return;
    }

    this.chartDistribucion = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: distData.labels,
        datasets: [
          {
            data: distData.data,
            backgroundColor: distData.colors,
            borderWidth: 2,
            borderColor: this.isDarkMode() ? '#1E293B' : '#FFFFFF',
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: colors.textColor,
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 14,
              font: { size: 11, family: 'system-ui' },
            },
          },
          tooltip: {
            backgroundColor: colors.tooltipBg,
            titleColor: colors.tooltipText,
            bodyColor: colors.tooltipText,
            borderColor: colors.tooltipBorder,
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: (context) => {
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const valor = context.raw;
                const porcentaje = total > 0 ? ((valor / total) * 100).toFixed(1) : 0;
                return ` ${context.label}: ${valor.toLocaleString('es-ES', { minimumFractionDigits: 2 })} € (${porcentaje}%)`;
              },
            },
          },
        },
      },
    });
  }

  actualizarGraficosPorAnio(anio) {
    fetch(`/api/graficos-data/?anio=${anio}`)
      .then((res) => res.json())
      .then((data) => {
        this.init(data);
      })
      .catch((err) => console.error('Error al actualizar gráficos:', err));
  }

  actualizarTema() {
    if (window.initialChartData) {
      this.init(window.initialChartData);
    }
  }
}

window.dashboardCharts = new DashboardChartsManager();
