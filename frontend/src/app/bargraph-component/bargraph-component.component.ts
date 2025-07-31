import { Component, effect, input, OnChanges } from '@angular/core';
import { AnalysisResult } from '../analysis-result';
import { ChartConfiguration ,ChartOptions} from 'chart.js';
import { NgChartsModule } from 'ng2-charts';

@Component({
  selector: 'app-bargraph-component',
  imports: [NgChartsModule],
  templateUrl: './bargraph-component.component.html',
  styleUrl: './bargraph-component.component.css'
})
export class BargraphComponentComponent {
   analysisData = input.required<AnalysisResult>();

  barData: ChartConfiguration<'bar'>['data'] = {
    labels: ['Low Risk', 'Medium Risk', 'High Risk'],
    datasets: [
      {
        data: [0, 0, 0],
        label: 'Risk Count',
        backgroundColor: ['#43e97b', '#fbc02d', '#ff4c7b']
      }
    ]
  };

  chartOptions: ChartOptions<'bar'> = {
    responsive: true,
    plugins: { legend: { position: 'bottom' } }
  };

  constructor() {
    // Update chart data whenever analysisData signal changes
    effect (() => {
      const d = this.analysisData();
      if (d) {
        this.barData.datasets[0].data = [
          d.low_risk,
          d.medium_risk,
          d.high_risk
        ];
      }
    });
  }
}

