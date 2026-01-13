import { useState, useEffect } from 'react';
import { X, HelpCircle, ChevronRight, Loader2 } from 'lucide-react';
import type { AskWhyQuestion, AskWhyAnswer } from '../../types';
import { mockAskWhyQuestions } from '../../services/mockData';
import { getAskWhyAnswer } from '../../services/api';

interface AskWhyModalProps {
  isOpen: boolean;
  onClose: () => void;
  dossierId: string;
  section: string;
  category: string;
}

export default function AskWhyModal({ isOpen, onClose, dossierId, section, category }: AskWhyModalProps) {
  const [questions, setQuestions] = useState<AskWhyQuestion[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<string | null>(null);
  const [answer, setAnswer] = useState<AskWhyAnswer | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      // Filter questions based on section
      const relevantQuestions = mockAskWhyQuestions.filter(q => {
        if (section === 'tools') return q.section === 'tools';
        if (section === 'cpo') return q.section === 'cpo' || q.section === 'pricing' || q.section === 'inventory';
        return q.section === 'pricing' || q.section === 'inventory' || q.section === 'overall';
      });
      setQuestions(relevantQuestions);
      setSelectedQuestion(null);
      setAnswer(null);
    }
  }, [isOpen, section]);

  async function handleQuestionSelect(questionId: string) {
    setSelectedQuestion(questionId);
    setLoading(true);
    try {
      const response = await getAskWhyAnswer(dossierId, section, questionId);
      setAnswer(response);
    } catch (error) {
      console.error('Failed to get answer:', error);
    } finally {
      setLoading(false);
    }
  }

  if (!isOpen) return null;

  const sectionLabel = section === 'tools' 
    ? 'Website Tools' 
    : section === 'cpo' 
    ? 'CPO Inventory' 
    : `${section.charAt(0).toUpperCase() + section.slice(1)} ${category.charAt(0).toUpperCase() + category.slice(1)}`;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                <HelpCircle className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Ask Why</h2>
                <p className="text-sm text-gray-500">{sectionLabel}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[60vh]">
            {/* Questions List */}
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Select a question:</h3>
              <div className="space-y-2">
                {questions.map((q) => (
                  <button
                    key={q.id}
                    onClick={() => handleQuestionSelect(q.id)}
                    className={`w-full text-left px-4 py-3 rounded-lg border transition-colors flex items-center justify-between ${
                      selectedQuestion === q.id
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700'
                    }`}
                  >
                    <span className="text-sm">{q.question}</span>
                    <ChevronRight className={`w-4 h-4 ${selectedQuestion === q.id ? 'text-blue-500' : 'text-gray-400'}`} />
                  </button>
                ))}
              </div>
            </div>

            {/* Answer Section */}
            {selectedQuestion && (
              <div className="border-t border-gray-200 pt-6">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Answer:</h3>
                
                {loading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                  </div>
                ) : answer ? (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-gray-800 mb-4">{answer.answer}</p>
                    
                    {answer.details.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-gray-600">Key factors:</p>
                        <ul className="space-y-2">
                          {answer.details.map((detail, i) => (
                            <li key={i} className="flex items-start text-sm text-gray-700">
                              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full mt-2 mr-2 flex-shrink-0"></span>
                              {detail}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : null}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
            <p className="text-xs text-gray-500 text-center">
              Answers are generated based on your latest dossier data. For more detailed analysis, contact your account manager.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
