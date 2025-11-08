import { Component, inject, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from "./header/header.component";
import { FormsModule } from '@angular/forms';
import { FileUploadService } from './file-upload.service';
import { AnalysisResult } from './analysis-result';
import { BargraphComponentComponent } from "./bargraph-component/bargraph-component.component";
import { PiechartComponentComponent } from "./piechart-component/piechart-component.component";
import { CommonModule, DecimalPipe } from '@angular/common';

const DEFAULT_ANALYSIS_RESULT: AnalysisResult = {
  low_risk: 0,
  medium_risk: 0,
  high_risk: 0,
  document_risk_score: 0,
  document_risk_level: ""
};

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HeaderComponent, FormsModule, BargraphComponentComponent, PiechartComponentComponent, CommonModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'frontend';

  // UI signals
  isloading = signal<boolean>(false);
  isinputgiven = signal<boolean>(true);
  anlayze = signal<boolean>(false);
  showvisualization = signal<boolean>(false);

  analysisData = signal<AnalysisResult>(DEFAULT_ANALYSIS_RESULT);

  // New: summary and risky clauses
  contentSummary = '';
  totalRisky = 0;
  documentScoreText = '';

  private fileService = inject(FileUploadService);

  onfileselect(inputfile: HTMLInputElement) {
    const files = inputfile.files;
    if (files && files.length > 0) {
      const file = files[0];
      const formData = new FormData();
      formData.append('file', file);

      // UI state
      this.isloading.set(true);
      this.isinputgiven.set(false);

      // Call service to analyze AND summarize (service returns merged object)
      this.fileService.analyzeAndSummarize(formData).subscribe({
        next: (result: any) => {
          this.isloading.set(false);
          // result contains: analyzeResult and summarizeResult (merged by service)
          if (result.analyze) {
            this.analysisData.set(result.analyze);
          }
          // Summarization
          if (result.summarize) {
            this.contentSummary = result.summarize.content_summary || '';
            this.totalRisky = result.summarize.total_risky_clauses || (result.summarize.total_risky || 0);
          } else {
            this.contentSummary = '';
            this.totalRisky = 0;
          }

          // Format document score as percent string
          const score = this.analysisData().document_risk_score ?? 0;
          this.documentScoreText = (score * 100).toFixed(2) + '%';

          this.showvisualization.set(true);
          this.anlayze.set(true);
          console.log('Analysis result:', this.analysisData());
          console.log('Summary result:', this.contentSummary);
        },
        error: (err) => {
          this.isloading.set(false);
          this.isinputgiven.set(true);
          console.error('Analysis failed', err);
          alert('Analysis failed, please try again');
        }
      });
    }
  }

  downloadClausesCsv() {
    // this will open server endpoint that serves the new CSV of clause locations
    const url = `${this.fileService.API_URL}/download_clauses`;
    window.open(url, '_blank');
  }

  // helpers for template usage
  isloading$ = this.isloading;
  isinputgiven$ = this.isinputgiven;
  showvisualization$ = this.showvisualization;
  anlayze$ = this.anlayze;

  isloadingFn = () => this.isloading();
  isinputgivenFn = () => this.isinputgiven();
  showvisualizationFn = () => this.showvisualization();
  analysisDataFn = () => this.analysisData();

  ngAfterViewChecked(): void {
    try {
      const summaryEl = document.querySelector('.doc-summary');
      if (summaryEl) {
        // scroll smoothly to summary only when it exists
        (summaryEl as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch (err) {
      // don't break UI on DOM access problems
      // keep silent or console.debug if you want:
      // console.debug('scroll failed', err);
    }
  }
}



