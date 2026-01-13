import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Check, X, HelpCircle, ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { Dossier, VehicleTypeData } from '../types';
import { getDossier } from '../services/api';
import AskWhyModal from '../components/dossier/AskWhyModal';

const TOOL_LABELS: Record<string, string> = {
  payment_calculator: 'Payment Calculator',
  apr_disclosure: 'APR Disclosure',
  lease_payment_options: 'Lease Payment Options',
  pre_qualification_tool: 'Pre-Qualification Tool',
  trade_in_tool: 'Trade-In Tool',
  online_finance_application: 'Online Finance Application',
  srp_payments_shown: 'SRP Payments Shown',
  vdp_payments_shown: 'VDP Payments Shown',
};

export default function DossierView() {
  const { id } = useParams<{ id: string }>();
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    new: true,
    used: false,
    cpo: false,
  });
  const [askWhyModal, setAskWhyModal] = useState<{ open: boolean; section: string; category: string }>({
    open: false,
    section: '',
    category: '',
  });

  useEffect(() => {
    if (id) {
      loadDossier(id);
    }
  }, [id]);

  async function loadDossier(dossierId: string) {
    try {
      const data = await getDossier(dossierId);
      setDossier(data);
    } catch (error) {
      console.error('Failed to load dossier:', error);
    } finally {
      setLoading(false);
    }
  }

  function toggleSection(section: string) {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  }

  function formatDate(dateString: string) {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  }

  function formatPrice(price: number) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  }

  function formatPercent(value: number) {
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
  }

  function getPercentColor(value: number) {
    if (value > 3) return 'text-red-600';
    if (value < -3) return 'text-green-600';
    return 'text-gray-600';
  }

  function getPercentIcon(value: number) {
    if (value > 1) return <TrendingUp className="w-4 h-4" />;
    if (value < -1) return <TrendingDown className="w-4 h-4" />;
    return <Minus className="w-4 h-4" />;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!dossier) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Dossier not found</p>
        <Link to="/" className="text-blue-600 hover:text-blue-700 mt-4 inline-block">
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const renderInventoryTable = (data: VehicleTypeData, category: string, condition: string) => (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50">
            <th className="text-left py-3 px-4 font-medium text-gray-600">Metric</th>
            <th className="text-center py-3 px-4 font-medium text-blue-600">You</th>
            {dossier.competitors.map((comp, i) => (
              <th key={i} className="text-center py-3 px-4 font-medium text-gray-600">
                {comp.name.length > 12 ? comp.name.slice(0, 12) + '...' : comp.name}
              </th>
            ))}
            <th className="text-center py-3 px-4 font-medium text-gray-600 bg-gray-100">Market Avg</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-gray-100">
            <td className="py-3 px-4 font-medium text-gray-700">Total Count</td>
            <td className="text-center py-3 px-4 font-semibold text-blue-600">{data.host.count}</td>
            {data.competitors.map((comp, i) => (
              <td key={i} className="text-center py-3 px-4 text-gray-700">{comp.count}</td>
            ))}
            <td className="text-center py-3 px-4 text-gray-600 bg-gray-50">{data.market_avg.count}</td>
          </tr>
          <tr className="border-b border-gray-100">
            <td className="py-3 px-4 font-medium text-gray-700">Avg Price</td>
            <td className="text-center py-3 px-4 font-semibold text-blue-600">{formatPrice(data.host.avg_price)}</td>
            {data.competitors.map((comp, i) => (
              <td key={i} className="text-center py-3 px-4 text-gray-700">{formatPrice(comp.avg_price)}</td>
            ))}
            <td className="text-center py-3 px-4 text-gray-600 bg-gray-50">{formatPrice(data.market_avg.avg_price)}</td>
          </tr>
          <tr>
            <td className="py-3 px-4 font-medium text-gray-700">vs Market</td>
            <td className="text-center py-3 px-4">
              <span className={`inline-flex items-center space-x-1 font-semibold ${getPercentColor(data.host.vs_market)}`}>
                {getPercentIcon(data.host.vs_market)}
                <span>{formatPercent(data.host.vs_market)}</span>
              </span>
            </td>
            {data.competitors.map((comp, i) => (
              <td key={i} className="text-center py-3 px-4">
                <span className={`inline-flex items-center space-x-1 ${getPercentColor(comp.vs_market)}`}>
                  {getPercentIcon(comp.vs_market)}
                  <span>{formatPercent(comp.vs_market)}</span>
                </span>
              </td>
            ))}
            <td className="text-center py-3 px-4 text-gray-400 bg-gray-50">—</td>
          </tr>
        </tbody>
      </table>
      <div className="flex justify-end mt-2">
        <button
          onClick={() => setAskWhyModal({ open: true, section: condition, category })}
          className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          <HelpCircle className="w-4 h-4 mr-1" />
          Ask Why
        </button>
      </div>
    </div>
  );

  const renderConditionSection = (condition: 'new' | 'used' | 'cpo', label: string) => {
    const data = dossier.inventory[condition];
    const isExpanded = expandedSections[condition];

    return (
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          onClick={() => toggleSection(condition)}
          className="w-full flex items-center justify-between px-6 py-4 bg-gray-50 hover:bg-gray-100 transition-colors"
        >
          <h3 className="text-lg font-semibold text-gray-900">{label} Vehicles</h3>
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          )}
        </button>

        {isExpanded && (
          <div className="p-6 space-y-8">
            <div>
              <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center">
                <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                Trucks
              </h4>
              {renderInventoryTable(data.trucks, 'trucks', condition)}
            </div>

            <div>
              <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                SUVs
              </h4>
              {renderInventoryTable(data.suvs, 'suvs', condition)}
            </div>

            <div>
              <h4 className="text-md font-semibold text-gray-800 mb-4 flex items-center">
                <span className="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
                Sedans
              </h4>
              {renderInventoryTable(data.sedans, 'sedans', condition)}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            to="/"
            className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-2"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Competitive Analysis Dossier</h1>
          <p className="mt-1 text-gray-500">Generated: {formatDate(dossier.generated_at)}</p>
        </div>
      </div>

      {/* Tool Comparison Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900">Website Tool Comparison</h2>
          <p className="text-sm text-gray-500 mt-1">Features available on each dealership website</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left py-3 px-4 font-medium text-gray-600">Tool</th>
                <th className="text-center py-3 px-4 font-medium text-blue-600">You</th>
                {dossier.competitors.map((comp, i) => (
                  <th key={i} className="text-center py-3 px-4 font-medium text-gray-600">
                    {comp.name.length > 12 ? comp.name.slice(0, 12) + '...' : comp.name}
                  </th>
                ))}
                <th className="text-center py-3 px-4 font-medium text-gray-600 bg-gray-100">Market %</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(dossier.tool_comparison).map(([key, data]) => (
                <tr key={key} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium text-gray-700">{TOOL_LABELS[key] || key}</td>
                  <td className="text-center py-3 px-4">
                    {data.host ? (
                      <span className="inline-flex items-center justify-center w-6 h-6 bg-green-100 text-green-600 rounded-full">
                        <Check className="w-4 h-4" />
                      </span>
                    ) : (
                      <span className="inline-flex items-center justify-center w-6 h-6 bg-red-100 text-red-600 rounded-full">
                        <X className="w-4 h-4" />
                      </span>
                    )}
                  </td>
                  {data.competitors.map((hasIt: boolean, i: number) => (
                    <td key={i} className="text-center py-3 px-4">
                      {hasIt ? (
                        <span className="inline-flex items-center justify-center w-6 h-6 bg-green-100 text-green-600 rounded-full">
                          <Check className="w-4 h-4" />
                        </span>
                      ) : (
                        <span className="inline-flex items-center justify-center w-6 h-6 bg-red-100 text-red-600 rounded-full">
                          <X className="w-4 h-4" />
                        </span>
                      )}
                    </td>
                  ))}
                  <td className="text-center py-3 px-4 bg-gray-50">
                    <span className={`font-medium ${data.market_pct >= 75 ? 'text-green-600' : data.market_pct >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {data.market_pct}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 flex justify-end">
          <button
            onClick={() => setAskWhyModal({ open: true, section: 'tools', category: 'all' })}
            className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            <HelpCircle className="w-4 h-4 mr-1" />
            Ask Why
          </button>
        </div>
      </div>

      {/* Inventory Comparison Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900">Inventory Comparison</h2>
          <p className="text-sm text-gray-500 mt-1">Vehicle inventory and pricing analysis by condition and type</p>
        </div>

        <div className="p-6 space-y-4">
          {renderConditionSection('new', 'New')}
          {renderConditionSection('used', 'Used')}
          {renderConditionSection('cpo', 'Certified Pre-Owned (CPO)')}
        </div>
      </div>

      {/* Ask Why Modal */}
      <AskWhyModal
        isOpen={askWhyModal.open}
        onClose={() => setAskWhyModal({ open: false, section: '', category: '' })}
        dossierId={dossier.id}
        section={askWhyModal.section}
        category={askWhyModal.category}
      />
    </div>
  );
}
