// Typed API responses for the Hijacking Retail Opportunity Decision Engine.
// The frontend never computes scores or recommendations: every value here
// originates from the backend (or, in Demo mode, from labelled fixtures).

export type ActionType = "TEST" | "CONTACT" | "RESEARCH" | "MONITOR" | "REJECT";

export type OriginBadge = "LIVE" | "DEMO" | "REPLAY" | "CALCULATED" | "MANUAL REVIEW";

export type RunMode = "demo" | "live";

export type StageStatus = "pending" | "running" | "complete" | "partial" | "failed";

export type ReviewStatus = "approved" | "rejected" | "pending";

export interface SourceSet {
  id: string;
  name: string;
  description: string;
  scope: "global" | "swiss";
  sourceCount: number;
}

export interface DiscoveryRunInput {
  category: string;
  targetMarket: string;
  sourceSetId: string;
  observationPeriod: "30" | "90" | "180";
  maxOpportunities: 3 | 5 | 10;
  focusKeywords?: string;
}

export interface DiscoveryStage {
  key: string;
  label: string;
  status: StageStatus;
  detail?: string;
}

export interface DiscoveryRun {
  id: string;
  mode: RunMode;
  status: StageStatus;
  startedAt: string;
  sourceSetId: string;
  sourceSetName: string;
  category: string;
  targetMarket: string;
  rawSignals: number;
  normalizedSignals: number;
  clusters: number;
  warnings: string[];
  stages: DiscoveryStage[];
}

export interface OpportunitySummary {
  id: string;
  runId: string;
  rank: number;
  name: string;
  strongestMarket: string;
  globalSignal: number; // 0-100
  swissFit: number; // 0-100
  swissCoverage: "none" | "partial" | "well-covered";
  opportunityScore: number; // 0-100
  confidence: number; // 0-100
  action: ActionType;
  mainMissingEvidence: string;
  discoveryStatus: StageStatus;
  origin: OriginBadge;
}

export interface ScoreItem {
  key: string;
  label: string;
  value: number; // 0-100
  origin: OriginBadge;
  explanation: string;
  calculatedAt: string;
}

export interface ClusterRationale {
  rawSignals: number;
  independentSources: number;
  markets: string[];
  brands: string[];
  products: string[];
  firstObserved: string;
  latestObserved: string;
  dominantProductType: string;
  dominantFeatures: string[];
  dominantMaterials: string[];
  dominantSegment: string;
  dominantOccasion: string;
  groupingExplanation: string;
  matchedTerms: string[];
}

export interface TransferFactor {
  key: string;
  label: string;
  value: number;
  reason: string;
  basis: string;
  confidence: number;
  limitations: string;
  heuristic: boolean;
}

export interface OpportunityDetail extends OpportunitySummary {
  productCategory: string;
  earliestMarket: string;
  decisionSummary: string;
  scoreBreakdown: ScoreItem[];
  confidenceBreakdown: ScoreItem[];
  rationale: ClusterRationale;
  transferability: TransferFactor[];
  risks: {
    counterSignals: string[];
    risks: string[];
    missingEvidence: string[];
    internalDataRequired: string[];
    extractionLimitations: string[];
  };
  recommendation: Recommendation;
  testPlan?: TestPlan;
}

export interface EvidenceRecord {
  id: string;
  source: string;
  sourceType: string;
  market: string;
  date: string;
  signal: string;
  brand: string;
  featureOrMaterial: string;
  price: string;
  direction: "supporting" | "counter" | "neutral";
  credibility: number;
  origin: OriginBadge;
  url: string;
  rawTitle: string;
  rawDescription: string;
  normalizedProductType: string;
  normalizedFeatures: string[];
  matchedTerms: string[];
  limitations: string;
  artifactRef: string;
}

export interface RetailerCoverage {
  id: string;
  retailer: string;
  approvedMatches: number;
  pendingMatches: number;
  rejectedMatches: number;
  brands: string[];
  priceRange: string;
  relevantFeatures: string[];
  availability: string;
  scanStatus: StageStatus;
  scanDate: string;
  origin: OriginBadge;
}

export interface ScanItem {
  id: string;
  productName: string;
  brand: string;
  price: string;
  features: string[];
  retailer: string;
  productUrl: string;
  matchScore: number;
  matchedKeywords: string[];
  extractionOrigin: OriginBadge;
  reviewStatus: ReviewStatus;
  reviewNote?: string;
}

export interface Recommendation {
  action: ActionType;
  triggeredRule: string;
  rationale: string;
  supportingEvidence: string[];
  preventingEvidence: string[];
  nextStep: string;
  origin: OriginBadge;
  complete: boolean;
}

export interface TestPlan {
  productScope: string;
  unitRange: string;
  channel: string;
  duration: string;
  targetCustomer: string;
  primaryMetric: string;
  secondaryMetrics: string[];
  successThreshold: string;
  stopCondition: string;
  assumptions: string[];
}

export interface SourceStatus {
  id: string;
  name: string;
  sourceType: string;
  geography: string;
  domain: string;
  scope: "global" | "swiss";
  active: boolean;
  lastSuccess: string | null;
  lastError: string | null;
  supportedMode: string;
  signalsCollected: number;
}

// ---- Opportunity Map ----

export interface MapEvidenceRef {
  source: string;
  date: string;
  product: string;
  brand: string;
  feature: string;
  strength: number; // 0-100 credibility
  url: string;
  direction: "supporting" | "counter" | "neutral";
}

export interface MapMarket {
  id: string;
  country: string;
  lat: number;
  lng: number;
  signalStrength: number; // 0-100 → marker size (global momentum)
  confidence: number; // 0-100 → marker opacity
  evidenceCount: number;
  action: ActionType; // → marker color (recommended action)
  isSwiss: boolean;
  opportunityIds: string[];
  evidence: MapEvidenceRef[];
  origin: OriginBadge;
}

export interface MapConnection {
  id: string;
  sourceMarket: string;
  targetMarket: string;
  opportunityId: string;
  transferabilityScore: number;
  swissGapScore: number;
}

export interface MapOpportunity extends OpportunitySummary {
  earliestMarket: string;
  swissGap: number; // 0-100, higher = more under-served in Switzerland
  signalCount: number;
  sourceCount: number;
  marketCount: number;
  markets: string[];
  mainSupportingEvidence: string;
}

export interface MapSummary {
  totalOpportunities: number;
  totalMarkets: number;
  totalSources: number;
  highestConfidence: number;
  highestSwissGap: number;
  strongestOpportunity: { id: string; name: string; confidence: number };
  highestGapOpportunity: { id: string; name: string; swissGap: number };
}

export interface OpportunityMapData {
  opportunities: MapOpportunity[];
  markets: MapMarket[];
  connections: MapConnection[];
  summary: MapSummary;
}
