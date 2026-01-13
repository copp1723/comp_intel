import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, ExternalLink, Save, AlertCircle, CheckCircle, Clock, FileText } from 'lucide-react';
import type { User, DossierSummary, CompetitorFormData } from '../types';
import { getCompetitors, saveCompetitors, getDossierList } from '../services/api';

interface DashboardProps {
  user: User | null;
}

export default function Dashboard({ user }: DashboardProps) {
  const [competitors, setCompetitors] = useState<CompetitorFormData[]>([
    { url: '', name: '' },
    { url: '', name: '' },
    { url: '', name: '' },
    { url: '', name: '' },
  ]);
  const [dossiers, setDossiers] = useState<DossierSummary[]>([]);
  const [nextScrape, setNextScrape] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [competitorData, dossierData] = await Promise.all([
        getCompetitors(),
        getDossierList(),
      ]);

      // Fill in competitor data
      const filledCompetitors: CompetitorFormData[] = [
        { url: '', name: '' },
        { url: '', name: '' },
        { url: '', name: '' },
        { url: '', name: '' },
      ];
      competitorData.competitors.forEach((c, i) => {
        if (i < 4) {
          filledCompetitors[i] = { url: c.url, name: c.name };
        }
      });
      setCompetitors(filledCompetitors);
      setNextScrape(competitorData.nextScrape);
      setDossiers(dossierData.slice(0, 5));
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaveSuccess(false);
    try {
      const validCompetitors = competitors.filter(c => c.url && c.name);
      await saveCompetitors(validCompetitors);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save competitors:', error);
    } finally {
      setSaving(false);
    }
  }

  function updateCompetitor(index: number, field: 'url' | 'name', value: string) {
    const updated = [...competitors];
    updated[index] = { ...updated[index], [field]: value };
    setCompetitors(updated);
  }

  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  function formatNextScrape(dateString: string) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    }) + ' at midnight';
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-gray-500">
          Manage your competitor analysis and view your dossiers
        </p>
      </div>

      {/* Dealership Info Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Your Dealership</h2>
            <p className="text-2xl font-bold text-blue-600 mt-1">{user?.dealershipName}</p>
            {user?.dealershipUrl && (
              <a
                href={user.dealershipUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-sm text-gray-500 hover:text-blue-600 mt-2"
              >
                {user.dealershipUrl}
                <ExternalLink className="w-3 h-3 ml-1" />
              </a>
            )}
          </div>
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center text-blue-700">
              <Calendar className="w-5 h-5 mr-2" />
              <span className="text-sm font-medium">Next Analysis</span>
            </div>
            <p className="text-sm text-blue-600 mt-1">
              {nextScrape ? formatNextScrape(nextScrape) : 'Wednesday at midnight'}
            </p>
          </div>
        </div>
      </div>

      {/* Competitor URLs Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Competitor URLs</h2>
            <p className="text-sm text-gray-500 mt-1">
              Add up to 4 competitor dealership websites to track
            </p>
          </div>
          {saveSuccess && (
            <div className="flex items-center text-green-600 text-sm">
              <CheckCircle className="w-4 h-4 mr-1" />
              Saved successfully
            </div>
          )}
        </div>

        <div className="space-y-4">
          {competitors.map((competitor, index) => (
            <div key={index} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Competitor {index + 1} URL
                </label>
                <input
                  type="url"
                  value={competitor.url}
                  onChange={(e) => updateCompetitor(index, 'url', e.target.value)}
                  placeholder="https://competitor-dealership.com"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dealership Name
                </label>
                <input
                  type="text"
                  value={competitor.name}
                  onChange={(e) => updateCompetitor(index, 'name', e.target.value)}
                  placeholder="Competitor Dealership Name"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
                />
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 flex items-center justify-between">
          <div className="flex items-center text-sm text-gray-500">
            <AlertCircle className="w-4 h-4 mr-2" />
            Analysis runs automatically every Wednesday at midnight
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Competitors
              </>
            )}
          </button>
        </div>
      </div>

      {/* Recent Dossiers Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Recent Dossiers</h2>
            <p className="text-sm text-gray-500 mt-1">
              View your latest competitive analysis reports
            </p>
          </div>
          <Link
            to="/history"
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            View All History →
          </Link>
        </div>

        {dossiers.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No dossiers yet</p>
            <p className="text-sm text-gray-400 mt-1">
              Your first analysis will run on the next scheduled date
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Date</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Competitors</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">Action</th>
                </tr>
              </thead>
              <tbody>
                {dossiers.map((dossier) => (
                  <tr key={dossier.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="flex items-center">
                        <Calendar className="w-4 h-4 text-gray-400 mr-2" />
                        <span className="text-sm text-gray-900">{formatDate(dossier.generatedAt)}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        dossier.status === 'complete'
                          ? 'bg-green-100 text-green-800'
                          : dossier.status === 'processing'
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {dossier.status === 'complete' && <CheckCircle className="w-3 h-3 mr-1" />}
                        {dossier.status === 'processing' && <Clock className="w-3 h-3 mr-1" />}
                        {dossier.status.charAt(0).toUpperCase() + dossier.status.slice(1)}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-gray-600">{dossier.competitorCount} competitors</span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/dossier/${dossier.id}`}
                        className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium"
                      >
                        View Report
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
