import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, ExternalLink, CheckCircle, Clock, XCircle, FileText, Search } from 'lucide-react';
import type { DossierSummary } from '../types';
import { getDossierList } from '../services/api';

export default function History() {
  const [dossiers, setDossiers] = useState<DossierSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    loadDossiers();
  }, []);

  async function loadDossiers() {
    try {
      const data = await getDossierList();
      setDossiers(data);
    } catch (error) {
      console.error('Failed to load dossiers:', error);
    } finally {
      setLoading(false);
    }
  }

  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  function formatTime(dateString: string) {
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  const filteredDossiers = dossiers.filter(d => {
    if (statusFilter !== 'all' && d.status !== statusFilter) return false;
    if (searchTerm) {
      const date = formatDate(d.generatedAt).toLowerCase();
      return date.includes(searchTerm.toLowerCase());
    }
    return true;
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-yellow-600" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
    switch (status) {
      case 'complete':
        return `${baseClasses} bg-green-100 text-green-800`;
      case 'processing':
        return `${baseClasses} bg-yellow-100 text-yellow-800`;
      case 'failed':
        return `${baseClasses} bg-red-100 text-red-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  };

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
        <h1 className="text-2xl font-bold text-gray-900">Dossier History</h1>
        <p className="mt-1 text-gray-500">
          View all your past competitive analysis reports
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by date..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            >
              <option value="all">All</option>
              <option value="complete">Complete</option>
              <option value="processing">Processing</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Dossiers List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {filteredDossiers.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No dossiers found</p>
            {searchTerm || statusFilter !== 'all' ? (
              <p className="text-sm text-gray-400 mt-1">Try adjusting your filters</p>
            ) : (
              <p className="text-sm text-gray-400 mt-1">Your first analysis will appear here</p>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Date Generated</th>
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Time</th>
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Status</th>
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Competitors</th>
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Dossier ID</th>
                  <th className="text-right py-4 px-6 text-sm font-medium text-gray-500">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredDossiers.map((dossier, index) => (
                  <tr 
                    key={dossier.id} 
                    className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                      index === 0 ? 'bg-blue-50/30' : ''
                    }`}
                  >
                    <td className="py-4 px-6">
                      <div className="flex items-center">
                        <Calendar className="w-4 h-4 text-gray-400 mr-2" />
                        <span className="text-sm font-medium text-gray-900">
                          {formatDate(dossier.generatedAt)}
                        </span>
                        {index === 0 && (
                          <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                            Latest
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <span className="text-sm text-gray-600">{formatTime(dossier.generatedAt)}</span>
                    </td>
                    <td className="py-4 px-6">
                      <span className={getStatusBadge(dossier.status)}>
                        {getStatusIcon(dossier.status)}
                        <span className="ml-1">
                          {dossier.status.charAt(0).toUpperCase() + dossier.status.slice(1)}
                        </span>
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      <span className="text-sm text-gray-600">{dossier.competitorCount} competitors</span>
                    </td>
                    <td className="py-4 px-6">
                      <code className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                        {dossier.id}
                      </code>
                    </td>
                    <td className="py-4 px-6 text-right">
                      {dossier.status === 'complete' ? (
                        <Link
                          to={`/dossier/${dossier.id}`}
                          className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium"
                        >
                          View Report
                          <ExternalLink className="w-3 h-3 ml-1" />
                        </Link>
                      ) : dossier.status === 'processing' ? (
                        <span className="text-sm text-gray-400">Processing...</span>
                      ) : (
                        <span className="text-sm text-red-500">Failed</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Total Dossiers</span>
            <FileText className="w-5 h-5 text-gray-400" />
          </div>
          <p className="text-2xl font-bold text-gray-900 mt-2">{dossiers.length}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Completed</span>
            <CheckCircle className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-green-600 mt-2">
            {dossiers.filter(d => d.status === 'complete').length}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">This Month</span>
            <Calendar className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-blue-600 mt-2">
            {dossiers.filter(d => {
              const date = new Date(d.generatedAt);
              const now = new Date();
              return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
            }).length}
          </p>
        </div>
      </div>
    </div>
  );
}
