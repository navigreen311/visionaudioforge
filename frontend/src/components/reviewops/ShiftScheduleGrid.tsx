'use client';

import { useState } from 'react';

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

interface Reviewer {
  id: string;
  name: string;
  avatar: string;
}

interface SlotAssignment {
  reviewer: Reviewer;
  zone: string;
}

type TimeSlot = 'Morning' | 'Afternoon' | 'Night';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;
type Day = (typeof DAYS)[number];

const TIME_SLOTS: TimeSlot[] = ['Morning', 'Afternoon', 'Night'];

const SLOT_TIMES: Record<TimeSlot, string> = {
  Morning: '06:00 - 14:00',
  Afternoon: '14:00 - 22:00',
  Night: '22:00 - 06:00',
};

const SLOT_COLORS: Record<TimeSlot, string> = {
  Morning: 'bg-amber-50 border-amber-200',
  Afternoon: 'bg-sky-50 border-sky-200',
  Night: 'bg-indigo-50 border-indigo-200',
};

// ------------------------------------------------------------------
// Mock data for the schedule grid
// ------------------------------------------------------------------

const MOCK_REVIEWERS: Reviewer[] = [
  { id: 'r1', name: 'Alice M.', avatar: 'AM' },
  { id: 'r2', name: 'Brian K.', avatar: 'BK' },
  { id: 'r3', name: 'Carla S.', avatar: 'CS' },
  { id: 'r4', name: 'David L.', avatar: 'DL' },
];

function buildInitialSchedule(): Record<string, SlotAssignment | null> {
  const schedule: Record<string, SlotAssignment | null> = {};
  for (const day of DAYS) {
    for (const slot of TIME_SLOTS) {
      schedule[`${day}-${slot}`] = null;
    }
  }
  // Pre-fill some slots
  schedule['Mon-Morning'] = { reviewer: MOCK_REVIEWERS[0], zone: 'Zone A' };
  schedule['Mon-Afternoon'] = { reviewer: MOCK_REVIEWERS[1], zone: 'Zone B' };
  schedule['Tue-Morning'] = { reviewer: MOCK_REVIEWERS[2], zone: 'Zone A' };
  schedule['Wed-Night'] = { reviewer: MOCK_REVIEWERS[3], zone: 'Zone C' };
  schedule['Thu-Afternoon'] = { reviewer: MOCK_REVIEWERS[0], zone: 'Zone B' };
  schedule['Fri-Morning'] = { reviewer: MOCK_REVIEWERS[1], zone: 'Zone A' };
  schedule['Sat-Morning'] = { reviewer: MOCK_REVIEWERS[2], zone: 'Zone C' };
  return schedule;
}

// ------------------------------------------------------------------
// Assign Modal
// ------------------------------------------------------------------

interface AssignModalProps {
  day: Day;
  slot: TimeSlot;
  reviewers: Reviewer[];
  onAssign: (reviewerId: string, zone: string) => void;
  onClose: () => void;
}

function AssignModal({ day, slot, reviewers, onAssign, onClose }: AssignModalProps) {
  const [selectedReviewer, setSelectedReviewer] = useState('');
  const [zone, setZone] = useState('Zone A');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">
          Assign Slot
        </h3>
        <p className="text-sm text-gray-500 mb-4">
          {day} &middot; {slot} ({SLOT_TIMES[slot]})
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Reviewer</label>
            <select
              value={selectedReviewer}
              onChange={(e) => setSelectedReviewer(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Select reviewer...</option>
              {reviewers.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Zone</label>
            <select
              value={zone}
              onChange={(e) => setZone(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="Zone A">Zone A</option>
              <option value="Zone B">Zone B</option>
              <option value="Zone C">Zone C</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (selectedReviewer) {
                onAssign(selectedReviewer, zone);
              }
            }}
            disabled={!selectedReviewer}
            className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm text-white hover:bg-brand-700 disabled:opacity-40"
          >
            Assign
          </button>
        </div>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// Grid Cell
// ------------------------------------------------------------------

interface GridCellProps {
  assignment: SlotAssignment | null;
  slot: TimeSlot;
  onClick: () => void;
}

function GridCell({ assignment, slot, onClick }: GridCellProps) {
  if (!assignment) {
    return (
      <button
        onClick={onClick}
        className={`w-full h-full min-h-[72px] rounded-lg border-2 border-dashed border-gray-300
          flex items-center justify-center text-xs text-gray-400 hover:border-brand-400
          hover:text-brand-500 transition-colors cursor-pointer`}
      >
        Unassigned
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      className={`w-full h-full min-h-[72px] rounded-lg border ${SLOT_COLORS[slot]}
        p-2 flex flex-col items-center justify-center gap-1 hover:shadow-md transition-shadow cursor-pointer`}
    >
      <div className="w-7 h-7 rounded-full bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center">
        {assignment.reviewer.avatar}
      </div>
      <span className="text-xs font-medium text-gray-800 truncate max-w-full">
        {assignment.reviewer.name}
      </span>
      <span className="text-[10px] text-gray-500">{assignment.zone}</span>
    </button>
  );
}

// ------------------------------------------------------------------
// ShiftScheduleGrid (exported)
// ------------------------------------------------------------------

export default function ShiftScheduleGrid() {
  const [schedule, setSchedule] = useState<Record<string, SlotAssignment | null>>(buildInitialSchedule);
  const [assignTarget, setAssignTarget] = useState<{ day: Day; slot: TimeSlot } | null>(null);

  const handleAssign = (reviewerId: string, zone: string) => {
    if (!assignTarget) return;
    const reviewer = MOCK_REVIEWERS.find((r) => r.id === reviewerId);
    if (!reviewer) return;
    const key = `${assignTarget.day}-${assignTarget.slot}`;
    setSchedule((prev) => ({ ...prev, [key]: { reviewer, zone } }));
    setAssignTarget(null);
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-gray-700">Upcoming Schedule</h3>

      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          {/* Header row: days */}
          <div className="grid grid-cols-[100px_repeat(7,1fr)] gap-1 mb-1">
            <div /> {/* spacer */}
            {DAYS.map((day) => (
              <div key={day} className="text-center text-xs font-semibold text-gray-600 py-1">
                {day}
              </div>
            ))}
          </div>

          {/* Rows: time slots */}
          {TIME_SLOTS.map((slot) => (
            <div key={slot} className="grid grid-cols-[100px_repeat(7,1fr)] gap-1 mb-1">
              <div className="flex flex-col justify-center text-xs text-gray-500 pr-2 text-right">
                <span className="font-medium">{slot}</span>
                <span className="text-[10px]">{SLOT_TIMES[slot]}</span>
              </div>
              {DAYS.map((day) => {
                const key = `${day}-${slot}`;
                return (
                  <GridCell
                    key={key}
                    assignment={schedule[key]}
                    slot={slot}
                    onClick={() => setAssignTarget({ day, slot })}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Assign modal */}
      {assignTarget && (
        <AssignModal
          day={assignTarget.day}
          slot={assignTarget.slot}
          reviewers={MOCK_REVIEWERS}
          onAssign={handleAssign}
          onClose={() => setAssignTarget(null)}
        />
      )}
    </div>
  );
}
