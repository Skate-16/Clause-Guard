import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AnalysisResult } from './analysis-result';

@Injectable({
  providedIn: 'root'
})
export class FileUploadService {

  private http= inject(HttpClient);
  analyzeDocument(formData:FormData):Observable<AnalysisResult>{
      return this.http.post<AnalysisResult>('http://localhost:5000/analyze', formData);
  }
   downloadCsv(): void {
    window.open('http://localhost:5000/download', '_blank');
  }
}
