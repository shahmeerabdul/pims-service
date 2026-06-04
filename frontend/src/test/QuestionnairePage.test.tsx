import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import QuestionnairePage from '../pages/QuestionnairePage';
import { questionnairesApi } from '../services/api';

// Mock react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (str: string) => str,
    i18n: {
      changeLanguage: () => new Promise(() => {}),
      language: 'en',
    },
  }),
}));

// Mock the API service
vi.mock('../services/api', () => ({
  questionnairesApi: {
    getDetail: vi.fn(),
    createResponseSet: vi.fn(),
    saveDraftResponseSet: vi.fn(),
    submitResponseSet: vi.fn(),
  },
  groupsApi: {
    getGroups: vi.fn().mockResolvedValue({ data: [] }),
  }
}));

const mockQuestionnaire = {
  id: 'q-1',
  title: 'Longitudinal Scales',
  assessment_type: 'PSYCHOMETRIC',
  questions: [
    {
      id: 'ques-1',
      content: '[PERMA] How happy are you? | آپ کتنے خوش ہیں؟',
      type: 'SCALE',
      order: 1,
      required: true,
      options: [
        { id: 'opt-0', label: '0 - Never | کبھی نہیں', numeric_value: 0, order: 0 },
        { id: 'opt-10', label: '10 - Always | ہمیشہ', numeric_value: 10, order: 10 }
      ]
    },
    {
      id: 'ques-2',
      content: '[PERMA] How active are you? | آپ کتنے متحرک ہیں؟',
      type: 'SCALE',
      order: 2,
      required: true,
      options: [
        { id: 'opt-0', label: '0 - Never | کبھی نہیں', numeric_value: 0, order: 0 },
        { id: 'opt-10', label: '10 - Always | ہمیشہ', numeric_value: 10, order: 10 }
      ]
    },
    {
      id: 'ques-3',
      content: '[PHQ-9] Feeling down, depressed. | اداسی اور افسردگی۔',
      type: 'SCALE',
      order: 3,
      required: true,
      options: [
        { id: 'opt-p0', label: '0 - Not at all', numeric_value: 0, order: 0 },
        { id: 'opt-p3', label: '3 - Nearly every day', numeric_value: 3, order: 3 }
      ]
    }
  ]
};

const mockResponseSet = {
  id: 'rs-123',
  responses: []
};

const delay = (ms: number) => new Promise(res => setTimeout(res, ms));

describe('QuestionnairePage Scale-Grouped Paging and Autosave', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (questionnairesApi.getDetail as any).mockResolvedValue({ data: mockQuestionnaire });
    (questionnairesApi.createResponseSet as any).mockResolvedValue({ data: mockResponseSet });
  });

  it('groups questions by scale, displays bilingual columns, and handles step pagination', async () => {
    render(
      <MemoryRouter initialEntries={['/questionnaires/q-1']}>
        <Routes>
          <Route path="/questionnaires/:id" element={<QuestionnairePage />} />
        </Routes>
      </MemoryRouter>
    );

    // Verify loading state is shown initially
    expect(screen.getByText(/Loading questionnaire.../i)).toBeInTheDocument();

    // Verify first scale group (PERMA) questions are loaded
    await waitFor(() => {
      expect(screen.getByText('Scale 1 / 2')).toBeInTheDocument();
      expect(screen.getByText('PERMA Profiler')).toBeInTheDocument();
      // First question (bilingual)
      expect(screen.getByText('How happy are you?')).toBeInTheDocument();
      expect(screen.getByText('آپ کتنے خوش ہیں؟')).toBeInTheDocument();
      // Second question (bilingual)
      expect(screen.getByText('How active are you?')).toBeInTheDocument();
      expect(screen.getByText('آپ کتنے متحرک ہیں؟')).toBeInTheDocument();
      // Third question (PHQ-9) should NOT be visible yet
      expect(screen.queryByText('Feeling down, depressed.')).not.toBeInTheDocument();
    });

    // Continue button should be disabled initially (since required questions are not answered)
    const continueBtn = screen.getByRole('button', { name: /Continue/i });
    expect(continueBtn).toBeDisabled();
  });

  it('triggers debounced draft auto-saving when a response is updated', async () => {
    (questionnairesApi.saveDraftResponseSet as any).mockResolvedValue({ data: { success: true } });

    render(
      <MemoryRouter initialEntries={['/questionnaires/q-1']}>
        <Routes>
          <Route path="/questionnaires/:id" element={<QuestionnairePage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('PERMA Profiler')).toBeInTheDocument();
    });

    // We have options 0 and 10 for ques-1
    const buttons = screen.getAllByRole('button');
    // Let's find the '0' option for the first question
    const zeroButton = buttons.find(b => b.textContent?.includes('0') && !b.textContent.includes('10'));
    expect(zeroButton).toBeDefined();

    // Click '0' response for question 1
    fireEvent.click(zeroButton!);

    // Verify saveDraftResponseSet is NOT called immediately
    expect(questionnairesApi.saveDraftResponseSet).not.toHaveBeenCalled();

    // Wait for the 500ms debounce timeout to complete
    await delay(600);

    // Verify it is auto-saved with draft response data
    expect(questionnairesApi.saveDraftResponseSet).toHaveBeenCalledTimes(1);
    expect(questionnairesApi.saveDraftResponseSet).toHaveBeenCalledWith(
      'rs-123',
      expect.arrayContaining([
        expect.objectContaining({
          question_id: 'ques-1',
          selected_option_id: 'opt-0'
        })
      ])
    );
  });
});
