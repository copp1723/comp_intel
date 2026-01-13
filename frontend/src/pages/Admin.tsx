import { useState, useEffect } from 'react';
import { Search, Play, AlertTriangle, CheckCircle, Clock, XCircle, RefreshCw, Users, Download, FileSpreadsheet, FileText, Car } from 'lucide-react';
import type { AdminScrape } from '../types';
import { getAdminScrapes, triggerAdminScrape, searchUsers } from '../services/api';

export default function Admin() {
  const [scrapes, setScrapes] = useState<AdminScrape[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{ id: number; name: string }[]>([]);
  const [selectedUser, setSelectedUser] = useState<{ id: number; name: string } | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);

  useEffect(() => {
    loadScrapes();
  }, []);

  useEffect(() => {
    if (searchQuery.length >= 2) {
      searchForUsers(searchQuery);
    } else {
      setSearchResults([]);
      setShowDropdown(false);
    }
  }, [searchQuery]);

  async function loadScrapes() {
    try {
      const data = await getAdminScrapes();
      setScrapes(data);
    } catch (error) {
      console.error('Failed to load scrapes:', error);
    } finally {
      setLoading(false);
    }
  }

  async function searchForUsers(query: string) {
    try {
      const results = await searchUsers(query);
      setSearchResults(results);
      setShowDropdown(true);
    } catch (error) {
      console.error('Failed to search users:', error);
    }
  }

  async function handleTriggerScrape() {
    if (!selectedUser) return;

    setTriggering(true);
    try {
      await triggerAdminScrape(selectedUser.id);
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
      setSelectedUser(null);
      setSearchQuery('');
      loadScrapes(); // Refresh the list
    } catch (error) {
      console.error('Failed to trigger scrape:', error);
    } finally {
      setTriggering(false);
    }
  }

  function selectUser(user: { id: number; name: string }) {
    setSelectedUser(user);
    setSearchQuery(user.name);
    setShowDropdown(false);
  }

  function formatDateTime(dateString: string) {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  // Mock inventory download function
  async function handleDownloadInventory(format: 'csv' | 'xlsx' | 'json') {
    setDownloadingFormat(format);
    
    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Generate mock inventory data
    const mockInventory = [
      { vin: '1HGBH41JXMN109186', year: 2024, make: 'Honda', model: 'Accord', trim: 'EX-L', condition: 'New', price: 32500, mileage: 15, daysOnLot: 12 },
      { vin: '2T1BURHE5JC123456', year: 2023, make: 'Toyota', model: 'Camry', trim: 'SE', condition: 'Used', price: 24900, mileage: 18500, daysOnLot: 28 },
      { vin: '1FA6P8TH5L5123456', year: 2024, make: 'Ford', model: 'Mustang', trim: 'GT', condition: 'New', price: 45000, mileage: 8, daysOnLot: 5 },
      { vin: '5YJSA1E26MF123456', year: 2023, make: 'Tesla', model: 'Model 3', trim: 'Long Range', condition: 'CPO', price: 38500, mileage: 12000, daysOnLot: 15 },
      { vin: 'WVWZZZ3CZWE123456', year: 2024, make: 'Volkswagen', model: 'ID.4', trim: 'Pro S', condition: 'New', price: 52000, mileage: 22, daysOnLot: 8 },
      { vin: '1G1YY22G965123456', year: 2022, make: 'Chevrolet', model: 'Corvette', trim: 'Stingray', condition: 'Used', price: 68000, mileage: 8500, daysOnLot: 45 },
      { vin: 'JN1TANT31U0123456', year: 2024, make: 'Nissan', model: 'Altima', trim: 'SV', condition: 'New', price: 28500, mileage: 12, daysOnLot: 18 },
      { vin: '3MW5R1J05M8123456', year: 2023, make: 'BMW', model: '330i', trim: 'xDrive', condition: 'CPO', price: 42000, mileage: 15000, daysOnLot: 22 },
    ];

    let content: string;
    let mimeType: string;
    let filename: string;

    if (format === 'csv') {
      const headers = Object.keys(mockInventory[0]).join(',');
      const rows = mockInventory.map(item => Object.values(item).join(','));
      content = [headers, ...rows].join('\n');
      mimeType = 'text/csv';
      filename = `inventory_export_${new Date().toISOString().split('T')[0]}.csv`;
    } else if (format === 'json') {
      content = JSON.stringify(mockInventory, null, 2);
      mimeType = 'application/json';
      filename = `inventory_export_${new Date().toISOString().split('T')[0]}.json`;
    } else {
      // For xlsx, we'll create a CSV as a fallback (real implementation would use a library)
      const headers = Object.keys(mockInventory[0]).join(',');
      const rows = mockInventory.map(item => Object.values(item).join(','));
      content = [headers, ...rows].join('\n');
      mimeType = 'text/csv';
      filename = `inventory_export_${new Date().toISOString().split('T')[0]}.csv`;
    }

    // Create and trigger download
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setDownloadingFormat(null);
  }

  function getStatusBadge(status: string) {
    const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
    switch (status) {
      case 'complete':
        return (
          <span className={`${baseClasses} bg-green-100 text-green-800`}>
            <CheckCircle className="w-3 h-3 mr-1" />
            Complete
          </span>
        );
      case 'processing':
        return (
          <span className={`${baseClasses} bg-yellow-100 text-yellow-800`}>
            <Clock className="w-3 h-3 mr-1 animate-pulse" />
            Processing
          </span>
        );
      case 'pending':
        return (
          <span className={`${baseClasses} bg-blue-100 text-blue-800`}>
            <Clock className="w-3 h-3 mr-1" />
            Pending
          </span>
        );
      case 'failed':
        return (
          <span className={`${baseClasses} bg-red-100 text-red-800`}>
            <XCircle className="w-3 h-3 mr-1" />
            Failed
          </span>
        );
      default:
        return (
          <span className={`${baseClasses} bg-gray-100 text-gray-800`}>
            {status}
          </span>
        );
    }
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
        <h1 className="text-2xl font-bold text-gray-900">Admin Panel</h1>
        <p className="mt-1 text-gray-500">
          Manage manual scrapes, downloads, and system operations
        </p>
      </div>

      {/* Inventory Download Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center mb-6">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
            <Car className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Download Your Inventory</h2>
            <p className="text-sm text-gray-500">Export your dealership's inventory data for external use</p>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-medium text-gray-700">Current Inventory</p>
              <p className="text-xs text-gray-500">Last updated: {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-blue-600">155</p>
              <p className="text-xs text-gray-500">Total Vehicles</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-white rounded-lg p-2">
              <p className="text-lg font-semibold text-green-600">45</p>
              <p className="text-xs text-gray-500">New</p>
            </div>
            <div className="bg-white rounded-lg p-2">
              <p className="text-lg font-semibold text-blue-600">85</p>
              <p className="text-xs text-gray-500">Used</p>
            </div>
            <div className="bg-white rounded-lg p-2">
              <p className="text-lg font-semibold text-purple-600">25</p>
              <p className="text-xs text-gray-500">CPO</p>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700">Choose export format:</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              onClick={() => handleDownloadInventory('csv')}
              disabled={downloadingFormat !== null}
              className="flex items-center justify-center px-4 py-3 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {downloadingFormat === 'csv' ? (
                <RefreshCw className="w-5 h-5 text-green-600 mr-2 animate-spin" />
              ) : (
                <FileSpreadsheet className="w-5 h-5 text-green-600 mr-2" />
              )}
              <div className="text-left">
                <p className="text-sm font-medium text-green-700">CSV Format</p>
                <p className="text-xs text-green-600">Best for Excel</p>
              </div>
            </button>

            <button
              onClick={() => handleDownloadInventory('xlsx')}
              disabled={downloadingFormat !== null}
              className="flex items-center justify-center px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {downloadingFormat === 'xlsx' ? (
                <RefreshCw className="w-5 h-5 text-blue-600 mr-2 animate-spin" />
              ) : (
                <FileSpreadsheet className="w-5 h-5 text-blue-600 mr-2" />
              )}
              <div className="text-left">
                <p className="text-sm font-medium text-blue-700">Excel Format</p>
                <p className="text-xs text-blue-600">Native .xlsx</p>
              </div>
            </button>

            <button
              onClick={() => handleDownloadInventory('json')}
              disabled={downloadingFormat !== null}
              className="flex items-center justify-center px-4 py-3 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {downloadingFormat === 'json' ? (
                <RefreshCw className="w-5 h-5 text-purple-600 mr-2 animate-spin" />
              ) : (
                <FileText className="w-5 h-5 text-purple-600 mr-2" />
              )}
              <div className="text-left">
                <p className="text-sm font-medium text-purple-700">JSON Format</p>
                <p className="text-xs text-purple-600">For integrations</p>
              </div>
            </button>
          </div>
        </div>

        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start">
            <Download className="w-4 h-4 text-blue-600 mr-2 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-blue-700">
              <strong>Tip:</strong> Use CSV or Excel format for spreadsheet applications. JSON format is ideal for API integrations, 
              third-party tools, or custom data processing workflows.
            </p>
          </div>
        </div>
      </div>

      {/* Manual Scrape Trigger */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center mb-6">
          <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center mr-3">
            <Play className="w-5 h-5 text-orange-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Manual Scrape Trigger</h2>
            <p className="text-sm text-gray-500">Trigger an on-demand analysis for a specific user</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* User Search */}
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select User/Dealership
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setSelectedUser(null);
                }}
                onFocus={() => searchQuery.length >= 2 && setShowDropdown(true)}
                placeholder="Search by dealership name..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>

            {/* Search Results Dropdown */}
            {showDropdown && searchResults.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto">
                {searchResults.map((user) => (
                  <button
                    key={user.id}
                    onClick={() => selectUser(user)}
                    className="w-full text-left px-4 py-3 hover:bg-gray-50 flex items-center"
                  >
                    <Users className="w-4 h-4 text-gray-400 mr-2" />
                    <span className="text-sm text-gray-700">{user.name}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Warning Notice */}
          <div className="flex items-start p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mr-3 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-yellow-800 font-medium">Important Notice</p>
              <p className="text-sm text-yellow-700 mt-1">
                Scrapes can take up to 5 hours to complete depending on the number of competitors and website complexity. 
                The user will receive an email notification when the analysis is ready.
              </p>
            </div>
          </div>

          {/* Trigger Button */}
          <div className="flex items-center justify-between pt-2">
            {showSuccess && (
              <div className="flex items-center text-green-600 text-sm">
                <CheckCircle className="w-4 h-4 mr-1" />
                Scrape triggered successfully
              </div>
            )}
            {!showSuccess && <div />}
            <button
              onClick={handleTriggerScrape}
              disabled={!selectedUser || triggering}
              className="inline-flex items-center px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 focus:ring-2 focus:ring-orange-500 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {triggering ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Triggering...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Trigger Scrape Now
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Recent Admin Scrapes */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Recent Admin Scrapes</h2>
            <p className="text-sm text-gray-500 mt-1">History of manually triggered analyses</p>
          </div>
          <button
            onClick={loadScrapes}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>

        {scrapes.length === 0 ? (
          <div className="text-center py-12">
            <Play className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No admin scrapes yet</p>
            <p className="text-sm text-gray-400 mt-1">Triggered scrapes will appear here</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">User/Dealership</th>
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Triggered By</th>
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Started</th>
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Completed</th>
                  <th className="text-left py-4 px-6 text-sm font-medium text-gray-500">Status</th>
                </tr>
              </thead>
              <tbody>
                {scrapes.map((scrape) => (
                  <tr key={scrape.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-4 px-6">
                      <span className="text-sm font-medium text-gray-900">{scrape.userName}</span>
                    </td>
                    <td className="py-4 px-6">
                      <span className="text-sm text-gray-600">{scrape.triggeredBy}</span>
                    </td>
                    <td className="py-4 px-6">
                      <span className="text-sm text-gray-600">{formatDateTime(scrape.startedAt)}</span>
                    </td>
                    <td className="py-4 px-6">
                      <span className="text-sm text-gray-600">
                        {scrape.completedAt ? formatDateTime(scrape.completedAt) : '—'}
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      {getStatusBadge(scrape.status)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Total Triggered</span>
            <Play className="w-5 h-5 text-gray-400" />
          </div>
          <p className="text-2xl font-bold text-gray-900 mt-2">{scrapes.length}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Processing</span>
            <Clock className="w-5 h-5 text-yellow-500" />
          </div>
          <p className="text-2xl font-bold text-yellow-600 mt-2">
            {scrapes.filter(s => s.status === 'processing' || s.status === 'pending').length}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Completed</span>
            <CheckCircle className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-green-600 mt-2">
            {scrapes.filter(s => s.status === 'complete').length}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Failed</span>
            <XCircle className="w-5 h-5 text-red-500" />
          </div>
          <p className="text-2xl font-bold text-red-600 mt-2">
            {scrapes.filter(s => s.status === 'failed').length}
          </p>
        </div>
      </div>
    </div>
  );
}
