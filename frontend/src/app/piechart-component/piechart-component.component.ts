import { Component, effect, input } from '@angular/core';
import { AnalysisResult } from '../analysis-result';
import { ChartConfiguration, ChartOptions } from 'chart.js';
import { NgChartsConfiguration, NgChartsModule } from 'ng2-charts';

@Component({
  selector: 'app-piechart-component',
  imports: [NgChartsModule],
  templateUrl: './piechart-component.component.html',
  styleUrl: './piechart-component.component.css'
})
export class PiechartComponentComponent {
  analysisData = input.required<AnalysisResult>();

  pieData: ChartConfiguration<'pie'>['data'] = {
    labels: ['Low Risk', 'Medium Risk', 'High Risk'],
    datasets: [
      {
        data: [0, 0, 0],
        backgroundColor: ['#43e97b', '#fbc02d', '#ff4c7b']
      }
    ]
  };

  chartOptions: ChartOptions<'pie'> = {
    responsive: true,
    plugins: { legend: { position: 'bottom' } }
  };

  constructor() {
    effect(() => {
      const d = this.analysisData();
      if (d) {
        this.pieData.datasets[0].data = [
          d.low_risk,
          d.medium_risk,
          d.high_risk
        ];
      }
    });
  }

}
