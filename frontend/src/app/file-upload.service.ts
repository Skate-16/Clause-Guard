import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, forkJoin, map } from 'rxjs';
import { AnalysisResult } from './analysis-result';

@Injectable({
  providedIn: 'root'
})
export class FileUploadService {
  // adjust if your backend has a different origin or port
  API_URL = 'http://localhost:5000'; 

  constructor(private http: HttpClient) {}

  // Calls both endpoints and merges responses
  analyzeAndSummarize(formData: FormData): Observable<{ analyze?: AnalysisResult, summarize?: any }> {
    // if backend on different host set API_URL accordingly: e.g. 'http://127.0.0.1:5000'
    const analyze$ = this.http.post<AnalysisResult>(`${this.API_URL}/analyze`, formData);
    const summarize$ = this.http.post<any>(`${this.API_URL}/summarize`, formData);

    return forkJoin({ analyze: analyze$, summarize: summarize$ }).pipe(
      map((res) => res)
    );
  }

  // Keep old download behaviour if you had but we use new endpoint
  downloadOldCsv(): void {
    window.open(`${this.API_URL}/download`, '_blank');
  }

  // new download endpoint for clauses locations CSV
  downloadClausesCsv(): void {
    window.open(`${this.API_URL}/download_clauses`, '_blank');
  }
}
