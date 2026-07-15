import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '../pages/DashboardPage';
import api, { activitiesApi } from '../services/api';

vi.mock('../services/api', () => ({
  default: {
    get: vi.fn(),
  },
  questionnairesApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
  activitiesApi: {
    getSubmissions: vi.fn().mockResolvedValue({ data: [] }),
  },
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders instructions only on Day 1 of activities', async () => {
    const mockActivity = {
      id: 1,
      title: 'Activity 1',
      description: 'First day reflection',
      submitted_today: false,
      current_day: 1,
    };
    const mockProfile = {
      id: 1,
      full_name: 'Test User',
      current_experiment_day: 1,
      due_milestone: null,
    };

    (api.get as any).mockImplementation((url: string) => {
      if (url === '/activities/daily/current/') return Promise.resolve({ data: mockActivity });
      if (url === '/users/profile/') return Promise.resolve({ data: mockProfile });
      return Promise.reject(new Error('Unknown url'));
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('How to Participate / حصہ لینے کا طریقہ')).toBeInTheDocument();
      expect(screen.getByText('Day 1 of 7')).toBeInTheDocument();
    });
  });

  it('does not render instructions on Day 2 of activities', async () => {
    const mockActivity = {
      id: 2,
      title: 'Activity 2',
      description: 'Second day reflection',
      submitted_today: false,
      current_day: 2,
    };
    const mockProfile = {
      id: 1,
      full_name: 'Test User',
      current_experiment_day: 2,
      due_milestone: null,
    };

    (api.get as any).mockImplementation((url: string) => {
      if (url === '/activities/daily/current/') return Promise.resolve({ data: mockActivity });
      if (url === '/users/profile/') return Promise.resolve({ data: mockProfile });
      return Promise.reject(new Error('Unknown url'));
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.queryByText('How to Participate / حصہ لینے کا طریقہ')).not.toBeInTheDocument();
      expect(screen.getByText('Day 2 of 7')).toBeInTheDocument();
    });
  });

  it('renders previous daily entries and opens details modal on click', async () => {
    const mockActivity = {
      id: 2,
      title: 'Activity 2',
      description: 'Second day reflection',
      submitted_today: true,
      current_day: 2,
    };
    const mockProfile = {
      id: 1,
      full_name: 'Test User',
      current_experiment_day: 2,
      due_milestone: null,
    };
    const mockSubmissions = [
      {
        id: 10,
        activity_title: 'Day 1 Activity',
        entry_1: 'Gratitude item 1 text',
        entry_2: 'Gratitude item 2 text',
        entry_3: 'Gratitude item 3 text',
        submission_date: '2026-06-21T12:00:00Z',
      },
    ];

    (api.get as any).mockImplementation((url: string) => {
      if (url === '/activities/daily/current/') return Promise.resolve({ data: mockActivity });
      if (url === '/users/profile/') return Promise.resolve({ data: mockProfile });
      return Promise.reject(new Error('Unknown url'));
    });

    (activitiesApi.getSubmissions as any).mockResolvedValue({ data: mockSubmissions });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    // Verify Previous Entries section header and item are shown
    await waitFor(() => {
      expect(screen.getByText('Previous Daily Entries')).toBeInTheDocument();
      expect(screen.getByText('Day 1 Activity')).toBeInTheDocument();
    });

    // View button
    const viewBtn = screen.getByRole('button', { name: /View \/ دیکھیں/i });
    expect(viewBtn).toBeInTheDocument();

    // Modal is not visible initially
    expect(screen.queryByText('Gratitude item 1 text')).not.toBeInTheDocument();

    // Click View
    fireEvent.click(viewBtn);

    // Modal should render content
    await waitFor(() => {
      expect(screen.getByText('Gratitude item 1 text')).toBeInTheDocument();
      expect(screen.getByText('Gratitude item 2 text')).toBeInTheDocument();
      expect(screen.getByText('Gratitude item 3 text')).toBeInTheDocument();
      expect(screen.getByText('Reflection 1')).toBeInTheDocument();
    });

    // Close button
    const closeBtn = screen.getByRole('button', { name: /Close \/ بند کریں/i });
    fireEvent.click(closeBtn);

    // Modal should be dismissed
    await waitFor(() => {
      expect(screen.queryByText('Gratitude item 1 text')).not.toBeInTheDocument();
    });
  });

  it('renders bilingual consistency nudge and due milestone banner', async () => {
    const mockActivity = {
      id: 2,
      title: 'Activity 2',
      description: 'Second day reflection',
      submitted_today: false,
      current_day: 2,
    };
    const mockProfile = {
      id: 1,
      full_name: 'Test User',
      current_experiment_day: 2,
      due_milestone: 'SIGNUP',
      has_consecutive_misses: true,
      consecutive_misses_message: 'Missed reflection couple days | آپ کچھ دنوں سے انعکاسی تحریر لکھنے سے رہ گئے',
    };
    const mockQuestionnaires = [
      {
        id: 'mock-q-id',
        is_active: true,
        assessment_type: 'PSYCHOMETRIC',
      }
    ];

    (api.get as any).mockImplementation((url: string) => {
      if (url === '/activities/daily/current/') return Promise.resolve({ data: mockActivity });
      if (url === '/users/profile/') return Promise.resolve({ data: mockProfile });
      return Promise.reject(new Error('Unknown url'));
    });

    const { questionnairesApi } = await import('../services/api');
    (questionnairesApi.list as any).mockResolvedValue({ data: mockQuestionnaires });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    // Verify consistency nudge is bilingual
    await waitFor(() => {
      expect(screen.getByText('Consistency Nudge')).toBeInTheDocument();
      expect(screen.getByText('تسلسل کی یاد دہانی')).toBeInTheDocument();
      expect(screen.getByText('Missed reflection couple days')).toBeInTheDocument();
      expect(screen.getByText('آپ کچھ دنوں سے انعکاسی تحریر لکھنے سے رہ گئے')).toBeInTheDocument();
    });

    // Verify milestone banner is bilingual
    await waitFor(() => {
      expect(screen.getByText('Baseline Psychometric Scales Available')).toBeInTheDocument();
      expect(screen.getByText('بنیادی نفسیاتی پیمانے دستیاب ہیں')).toBeInTheDocument();
      expect(screen.getByText('Please complete the baseline assessment to finalize your signup.')).toBeInTheDocument();
      expect(screen.getByText('رجسٹریشن مکمل کرنے کے لیے براہِ کرم بنیادی جائزہ پورا کریں۔')).toBeInTheDocument();
      expect(screen.getByText(/Start Baseline Assessment/i)).toBeInTheDocument();
      expect(screen.getByText(/بنیادی جائزہ شروع کریں/i)).toBeInTheDocument();
    });
  });
});

