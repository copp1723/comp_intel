import type { User, Competitor, Dossier, DossierSummary, AskWhyQuestion, AskWhyAnswer, AdminScrape } from '../types';

// Mock User
export const mockUser: User = {
  id: 'user_001',
  email: 'dealer@example.com',
  name: 'John Smith',
  dealershipName: 'Smith Auto Group',
  dealershipUrl: 'https://smithautogroup.com',
  role: 'admin',
};

// Mock Competitors
export const mockCompetitors: Competitor[] = [
  { id: 1, url: 'https://competitor1ford.com', name: 'Competitor Ford', lastScraped: '2025-01-08T00:00:00Z' },
  { id: 2, url: 'https://competitor2toyota.com', name: 'Competitor Toyota', lastScraped: '2025-01-08T00:00:00Z' },
  { id: 3, url: 'https://competitor3honda.com', name: 'Competitor Honda', lastScraped: '2025-01-08T00:00:00Z' },
  { id: 4, url: 'https://competitor4chevy.com', name: 'Competitor Chevy', lastScraped: '2025-01-08T00:00:00Z' },
];

// Mock Dossier Summaries
export const mockDossierSummaries: DossierSummary[] = [
  { id: 'dossier_001', generatedAt: '2025-01-08T00:00:00Z', status: 'complete', competitorCount: 4 },
  { id: 'dossier_002', generatedAt: '2025-01-01T00:00:00Z', status: 'complete', competitorCount: 4 },
  { id: 'dossier_003', generatedAt: '2024-12-25T00:00:00Z', status: 'complete', competitorCount: 3 },
  { id: 'dossier_004', generatedAt: '2024-12-18T00:00:00Z', status: 'complete', competitorCount: 4 },
  { id: 'dossier_005', generatedAt: '2024-12-11T00:00:00Z', status: 'complete', competitorCount: 4 },
];

// Mock Full Dossier
export const mockDossier: Dossier = {
  id: 'dossier_001',
  generated_at: '2025-01-08T00:00:00Z',
  host: {
    name: 'Smith Auto Group',
    url: 'https://smithautogroup.com',
  },
  competitors: [
    { name: 'Competitor Ford', url: 'https://competitor1ford.com' },
    { name: 'Competitor Toyota', url: 'https://competitor2toyota.com' },
    { name: 'Competitor Honda', url: 'https://competitor3honda.com' },
    { name: 'Competitor Chevy', url: 'https://competitor4chevy.com' },
  ],
  tool_comparison: {
    payment_calculator: { host: true, competitors: [true, true, false, true], market_pct: 80 },
    apr_disclosure: { host: false, competitors: [true, true, true, true], market_pct: 100 },
    lease_payment_options: { host: true, competitors: [false, true, true, false], market_pct: 50 },
    pre_qualification_tool: { host: false, competitors: [true, false, true, true], market_pct: 75 },
    trade_in_tool: { host: true, competitors: [true, true, true, true], market_pct: 100 },
    online_finance_application: { host: false, competitors: [true, true, true, true], market_pct: 100 },
    srp_payments_shown: { host: true, competitors: [false, true, false, true], market_pct: 50 },
    vdp_payments_shown: { host: true, competitors: [true, true, true, true], market_pct: 100 },
  },
  inventory: {
    new: {
      trucks: {
        host: { count: 45, avg_price: 52000, vs_market: 2.5 },
        competitors: [
          { count: 62, avg_price: 48000, vs_market: -5.4 },
          { count: 38, avg_price: 55000, vs_market: 8.4 },
          { count: 55, avg_price: 51000, vs_market: 0.5 },
          { count: 41, avg_price: 49000, vs_market: -3.4 },
        ],
        market_avg: { count: 49, avg_price: 50750 },
      },
      suvs: {
        host: { count: 78, avg_price: 45000, vs_market: -1.2 },
        competitors: [
          { count: 85, avg_price: 46000, vs_market: 1.0 },
          { count: 72, avg_price: 44000, vs_market: -3.4 },
          { count: 90, avg_price: 47000, vs_market: 3.2 },
          { count: 68, avg_price: 45500, vs_market: -0.1 },
        ],
        market_avg: { count: 79, avg_price: 45625 },
      },
      sedans: {
        host: { count: 32, avg_price: 28000, vs_market: -2.8 },
        competitors: [
          { count: 28, avg_price: 29000, vs_market: 0.7 },
          { count: 45, avg_price: 27500, vs_market: -4.5 },
          { count: 38, avg_price: 30000, vs_market: 4.2 },
          { count: 35, avg_price: 28800, vs_market: 0.0 },
        ],
        market_avg: { count: 36, avg_price: 28825 },
      },
    },
    used: {
      trucks: {
        host: { count: 28, avg_price: 38000, vs_market: 5.5 },
        competitors: [
          { count: 35, avg_price: 35000, vs_market: -2.8 },
          { count: 22, avg_price: 37000, vs_market: 2.8 },
          { count: 40, avg_price: 34000, vs_market: -5.6 },
          { count: 30, avg_price: 36500, vs_market: 1.4 },
        ],
        market_avg: { count: 31, avg_price: 36000 },
      },
      suvs: {
        host: { count: 55, avg_price: 32000, vs_market: 3.2 },
        competitors: [
          { count: 48, avg_price: 30000, vs_market: -3.2 },
          { count: 62, avg_price: 31500, vs_market: 1.6 },
          { count: 45, avg_price: 31000, vs_market: 0.0 },
          { count: 58, avg_price: 32500, vs_market: 4.8 },
        ],
        market_avg: { count: 54, avg_price: 31000 },
      },
      sedans: {
        host: { count: 42, avg_price: 18000, vs_market: -5.3 },
        competitors: [
          { count: 38, avg_price: 19500, vs_market: 2.6 },
          { count: 50, avg_price: 18500, vs_market: -2.6 },
          { count: 35, avg_price: 20000, vs_market: 5.3 },
          { count: 45, avg_price: 18000, vs_market: -5.3 },
        ],
        market_avg: { count: 42, avg_price: 19000 },
      },
    },
    cpo: {
      trucks: {
        host: { count: 12, avg_price: 42000, vs_market: 2.4 },
        competitors: [
          { count: 18, avg_price: 40000, vs_market: -2.4 },
          { count: 8, avg_price: 43000, vs_market: 4.9 },
          { count: 15, avg_price: 41000, vs_market: 0.0 },
          { count: 10, avg_price: 40500, vs_market: -1.2 },
        ],
        market_avg: { count: 13, avg_price: 41000 },
      },
      suvs: {
        host: { count: 22, avg_price: 35000, vs_market: 0.0 },
        competitors: [
          { count: 25, avg_price: 34000, vs_market: -2.9 },
          { count: 18, avg_price: 36000, vs_market: 2.9 },
          { count: 28, avg_price: 35500, vs_market: 1.4 },
          { count: 20, avg_price: 34500, vs_market: -1.4 },
        ],
        market_avg: { count: 23, avg_price: 35000 },
      },
      sedans: {
        host: { count: 8, avg_price: 22000, vs_market: -4.3 },
        competitors: [
          { count: 12, avg_price: 23500, vs_market: 2.2 },
          { count: 6, avg_price: 22500, vs_market: -2.2 },
          { count: 10, avg_price: 24000, vs_market: 4.3 },
          { count: 9, avg_price: 22000, vs_market: -4.3 },
        ],
        market_avg: { count: 9, avg_price: 23000 },
      },
    },
  },
  ask_why_available: true,
};

// Mock Ask Why Questions
export const mockAskWhyQuestions: AskWhyQuestion[] = [
  { id: 'q1', question: 'Why is my average price higher/lower than competitors?', section: 'pricing' },
  { id: 'q2', question: 'Why do I have fewer/more vehicles in this category?', section: 'inventory' },
  { id: 'q3', question: 'Which specific vehicles are affecting my average price?', section: 'pricing' },
  { id: 'q4', question: 'Why don\'t I have this tool on my website?', section: 'tools' },
  { id: 'q5', question: 'How does my inventory mix compare to the market?', section: 'inventory' },
  { id: 'q6', question: 'Which competitor has the most competitive pricing?', section: 'pricing' },
  { id: 'q7', question: 'What is driving the price difference in this category?', section: 'pricing' },
  { id: 'q8', question: 'How does my CPO inventory compare to competitors?', section: 'cpo' },
  { id: 'q9', question: 'Which tools are most common among my competitors?', section: 'tools' },
  { id: 'q10', question: 'What is my competitive position in the market?', section: 'overall' },
];

// Mock Ask Why Answer
export const mockAskWhyAnswer: AskWhyAnswer = {
  question: 'Why is my average price 2.5% higher than the market?',
  answer: 'Your average truck price of $52,000 is 2.5% above the market average of $50,750. This is primarily driven by your inventory mix and trim level distribution.',
  details: [
    '3 high-end trim levels (Raptor, Limited) averaging $78,000',
    'Lower inventory count (45 vs market avg 49)',
    'Higher proportion of 2025 model year vehicles',
    'Competitor Ford has the most competitive pricing at $48,000 avg with 62 trucks',
  ],
};

// Mock Admin Scrapes
export const mockAdminScrapes: AdminScrape[] = [
  { id: 1, userId: 1, userName: 'La Fontaine Auto', triggeredBy: 'Charlie', startedAt: '2025-01-13T10:30:00Z', status: 'processing' },
  { id: 2, userId: 2, userName: 'Kunis Auto Group', triggeredBy: 'Joe', startedAt: '2025-01-12T14:00:00Z', completedAt: '2025-01-12T18:30:00Z', status: 'complete' },
  { id: 3, userId: 3, userName: 'Smith Auto Group', triggeredBy: 'Amanda', startedAt: '2025-01-10T09:00:00Z', completedAt: '2025-01-10T13:45:00Z', status: 'complete' },
];

// Helper function to get next Wednesday
export function getNextWednesday(): string {
  const now = new Date();
  const dayOfWeek = now.getDay();
  const daysUntilWednesday = (3 - dayOfWeek + 7) % 7 || 7;
  const nextWednesday = new Date(now);
  nextWednesday.setDate(now.getDate() + daysUntilWednesday);
  nextWednesday.setHours(0, 0, 0, 0);
  return nextWednesday.toISOString();
}
