import type { User, Competitor, CompetitorFormData, Dossier, DossierSummary, AskWhyAnswer, AdminScrape } from '../types';
import { mockUser, mockCompetitors, mockDossier, mockDossierSummaries, mockAskWhyAnswer, mockAdminScrapes, getNextWednesday } from './mockData';

// Simulated API delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// API Base URL - will be configured for production
const API_BASE = import.meta.env.VITE_API_BASE || '/api';

// For development, we use mock data
const USE_MOCK = true;

// User API
export async function getCurrentUser(): Promise<User> {
  if (USE_MOCK) {
    await delay(300);
    return mockUser;
  }
  const response = await fetch(`${API_BASE}/user/me`);
  return response.json();
}

// Competitors API
export async function getCompetitors(): Promise<{ competitors: Competitor[]; maxCompetitors: number; nextScrape: string }> {
  if (USE_MOCK) {
    await delay(300);
    return {
      competitors: mockCompetitors,
      maxCompetitors: 4,
      nextScrape: getNextWednesday(),
    };
  }
  const response = await fetch(`${API_BASE}/competitors`);
  const data = await response.json();
  return {
    competitors: data.competitors,
    maxCompetitors: data.max_competitors,
    nextScrape: data.next_scrape,
  };
}

export async function saveCompetitors(competitors: CompetitorFormData[]): Promise<{ success: boolean }> {
  if (USE_MOCK) {
    await delay(500);
    console.log('Saving competitors:', competitors);
    return { success: true };
  }
  const response = await fetch(`${API_BASE}/competitors`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ competitors }),
  });
  return response.json();
}

// Dossiers API
export async function getDossierList(): Promise<DossierSummary[]> {
  if (USE_MOCK) {
    await delay(300);
    return mockDossierSummaries;
  }
  const response = await fetch(`${API_BASE}/dossiers`);
  return response.json();
}

export async function getDossier(id: string): Promise<Dossier> {
  if (USE_MOCK) {
    await delay(500);
    return { ...mockDossier, id };
  }
  const response = await fetch(`${API_BASE}/dossiers/${id}`);
  return response.json();
}

export async function getAskWhyAnswer(dossierId: string, section: string, questionId: string): Promise<AskWhyAnswer> {
  if (USE_MOCK) {
    await delay(800);
    return mockAskWhyAnswer;
  }
  const response = await fetch(`${API_BASE}/dossiers/${dossierId}/ask-why?section=${section}&question=${questionId}`);
  return response.json();
}

// Admin API
export async function getAdminScrapes(): Promise<AdminScrape[]> {
  if (USE_MOCK) {
    await delay(300);
    return mockAdminScrapes;
  }
  const response = await fetch(`${API_BASE}/admin/scrapes`);
  return response.json();
}

export async function triggerAdminScrape(userId: number): Promise<{ success: boolean; scrapeId: number }> {
  if (USE_MOCK) {
    await delay(500);
    return { success: true, scrapeId: Date.now() };
  }
  const response = await fetch(`${API_BASE}/admin/scrape`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId }),
  });
  return response.json();
}

export async function searchUsers(query: string): Promise<{ id: number; name: string }[]> {
  if (USE_MOCK) {
    await delay(200);
    const users = [
      { id: 1, name: 'La Fontaine Auto' },
      { id: 2, name: 'Kunis Auto Group' },
      { id: 3, name: 'Smith Auto Group' },
      { id: 4, name: 'Johnson Motors' },
      { id: 5, name: 'Williams Automotive' },
    ];
    return users.filter(u => u.name.toLowerCase().includes(query.toLowerCase()));
  }
  const response = await fetch(`${API_BASE}/admin/users?search=${encodeURIComponent(query)}`);
  return response.json();
}
