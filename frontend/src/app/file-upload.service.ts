import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AnalysisResult } from './analysis-result';
import { environment } from '../environments/environment'; // keep this import

@Injectable({
  providedIn: 'root'
})
export class FileUploadService {

  private http = inject(HttpClient);

  analyzeDocument(formData: FormData): Observable<AnalysisResult> {
    return this.http.post<AnalysisResult>(
      `${environment.API_URL}/analyze`, 
      formData
    );
  }

  downloadCsv(): void {
    window.open(`${environment.API_URL}/download`, '_blank'); 
  }
}
