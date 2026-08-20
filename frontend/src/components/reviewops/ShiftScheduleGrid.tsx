'use client';

import { useEffect, useState } from 'react';

import { readWorkspaceId } from '@/lib/session';

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
// Deriving the week from real shifts
// ------------------------------------------------------------------
//
// This grid used to be four invented reviewers ("Alice M.", "Brian K."...) and
// seven hardcoded assignments, with an Assign modal that wrote into local state
// and nowhere else - so the schedule shown had never come from anywhere and the
// edits made to it went nowhere.
//
// The platform stores a shift as a reviewer plus a start and end time. It has no
// notion of a day-slot or a zone, so the grid derives the first from each
// shift's start time and no longer offers the second.

interface ShiftPayload {
  shift_id: string;
  reviewer_id: string | null;
  reviewer_name: string;
  start_time: string;
  end_time: string;
  active: boolean;
}

const DAY_INDEX: Record<number, Day> = {
  1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat', 0: 'Sun',
};

/** Which slot a shift belongs to, from the hour it starts. */
function slotFor(startedAt: string): TimeSlot {
  const hour = new Date(startedAt).getHours();
  if (hour >= 6 && hour < 14) return 'Morning';
  if (hour >= 14 && hour < 22) return 'Afternoon';
  return 'Night';
}

function initials(name: string): string {
  return (name || '?')
    .split(/[\s@.]+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
}

function scheduleFrom(shifts: ShiftPayload[]): Record<string, SlotAssignment | null> {
  const schedule: Record<string, SlotAssignment | null> = {};
  for (const day of DAYS) {
    for (const slot of TIME_SLOTS) schedule[`${day}-${slot}`] = null;
  }

  for (const shift of shifts) {
    if (!shift.start_time) continue;
    const day = DAY_INDEX[new Date(shift.start_time).getDay()];
    if (!day) continue;
    schedule[`${day}-${slotFor(shift.start_time)}`] = {
      reviewer: {
        id: shift.reviewer_id ?? shift.shift_id,
        name: shift.reviewer_name,
        avatar: initials(shift.reviewer_name),
      },
    };
  }

  return schedule;
}

// ------------------------------------------------------------------
// Grid cell
// ------------------------------------------------------------------

interface GridCellProps {
  assignment: SlotAssignment | null;
  slot: TimeSlot;
}

function GridCell({ assignment, slot }: GridCellProps) {
  // These were buttons opening an Assign modal that only wrote to local state.
  // A cell now reports what is scheduled and nothing else, because that is all
  // this component can truthfully do without a shift-assignment endpoint.
  if (!assignment) {
    return (
      <div
        className="w-full h-full min-h-[72px] rounded-lg border-2 border-dashed border-gray-300
          flex items-center justify-center text-xs text-gray-400"
      >
        Unassigned
      </div>
    );
  }

  return (
    <div
      className={`w-full h-full min-h-[72px] rounded-lg border ${SLOT_COLORS[slot]}
        p-2 flex flex-col items-center justify-center gap-1`}
    >
      <div className="w-7 h-7 rounded-full bg-brand-600 text-white text-[10px] font-bold flex items-center justify-center">
        {assignment.reviewer.avatar}
      </div>
      <span className="text-xs font-medium text-gray-800 truncate max-w-full">
        {assignment.reviewer.name}
      </span>
    </div>
  );
}

// ------------------------------------------------------------------
// ShiftScheduleGrid (exported)
// ------------------------------------------------------------------

export default function ShiftScheduleGrid() {
  const [schedule, setSchedule] = useState<Record<string, SlotAssignment | null>>(
    () => scheduleFrom([]),
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch(
          `/api/reviewops/shifts?workspace_id=${readWorkspaceId()}`,
        );
        if (res.ok) setSchedule(scheduleFrom(await res.json()));
      } catch {
        // An empty grid is the honest answer to a failed request.
      } finally {
        setLoading(false);
      }
    })();
  }, []);

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
                  <GridCell key={key} assignment={schedule[key]} slot={slot} />
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* The Assign modal that used to sit here only ever wrote to this
          component's own state. Shifts are created through "Create Shift"
          above, which posts to /api/reviewops/shifts. */}
      {!loading && Object.values(schedule).every((slot) => slot === null) && (
        <p className="text-sm text-gray-500">
          No shifts scheduled this week.
        </p>
      )}

    </div>
  );
}
