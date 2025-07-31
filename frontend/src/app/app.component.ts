import { Component, inject, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from "./header/header.component";
import { FormsModule } from '@angular/forms';
import { FileUploadService } from './file-upload.service';
import { AnalysisResult } from './analysis-result';
import { BargraphComponentComponent } from "./bargraph-component/bargraph-component.component";
import { PiechartComponentComponent } from "./piechart-component/piechart-component.component";
import { PercentPipe } from '@angular/common';
const DEFAULT_ANALYSIS_RESULT: AnalysisResult = {
  low_risk: 0,
  medium_risk: 0,
  high_risk: 0,
  document_risk_score: 0,
  document_risk_level: ""
}
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HeaderComponent, FormsModule, BargraphComponentComponent, PiechartComponentComponent,PercentPipe],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})

export class AppComponent {
  isloading = signal<boolean>(false);
  title = 'frontend';
  isinputgiven = signal<boolean>(true);
  anlayze = signal<boolean>(false);
  analysisData = signal<AnalysisResult>(DEFAULT_ANALYSIS_RESULT);
  showvisualization = signal<boolean>(false);

  private fileService = inject(FileUploadService);
  onfileselect(inputfile: HTMLInputElement) {
    const files = inputfile.files;
    if (files && files.length > 0) {
      const file = files[0];
      const formData = new FormData();
      formData.append('file', file);
      this.isloading.set(true);
      this.isinputgiven.set(false);

      this.fileService.analyzeDocument(formData).subscribe({
        next: (result: AnalysisResult) => {
          this.isloading.set(false);
          this.analysisData.set(result);
          this.showvisualization.set(true);
          this.anlayze.set(true)
          console.log(this.analysisData());

        },
        error: () => {
          this.isloading.set(false);
          alert('Anylsis failed please try again')
        }
      })
    }

  }

  downloadcsv() {
    this.fileService.downloadCsv();

  }

}
