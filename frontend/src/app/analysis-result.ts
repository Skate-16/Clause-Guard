export interface AnalysisResult {
  low_risk: number;
  medium_risk: number;
  high_risk: number;
 document_risk_score: number;
  
  document_risk_level: string;
}
