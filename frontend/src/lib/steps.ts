import type { CommandStep } from "@/lib/orchestrator";
import { SECTION_LABELS } from "@/lib/sections";
import type { SectionType } from "@/types/sections";

const LABELS: Record<string, string> = {
  transcribe: "Transcribing what you said",
  transcribed: "Reading your request",
  interpret: "Working out what you want",
  clarify: "Putting a question together",
  load_page: "Opening your page",
  generate_schema: "Choosing the sections",
  plan: "Planning the work",
  select_theme: "Choosing a palette",
  generate_copy: "Writing the {section} copy",
  select_image: "Finding a photo for the {section}",
  select_icon: "Picking the {section} icons",
  assemble_section: "Checking the {section} section",
  assemble_page: "Validating the page",
  save_draft: "Saving the draft",
  edit_content: "Applying your edit",
  replace_image: "Swapping the picture",
  add_section: "Adding the section",
  remove_section: "Removing the section",
  move_section: "Moving the {section} section",
  set_variant: "Changing the {section} layout",
  add_item: "Adding an entry to the {section} section",
  remove_item: "Removing an entry from the {section} section",
  move_item: "Reordering the {section} section",
  set_icon: "Changing an icon on the {section} section",
  set_theme: "Recolouring the page",
  approve_section: "Marking the {section} section as reviewed",
  regenerate_section: "Rewriting the {section} section",
};

export interface Progress {
  done: number;
  total: number;
  label: string;
}

function sectionName(section?: string | null) {
  if (!section) return "page";
  return SECTION_LABELS[section as SectionType] ?? section;
}

export function stepLabel(step: CommandStep): string {
  const template = LABELS[step.tool] ?? step.tool.replace(/_/g, " ");
  return template.replace("{section}", sectionName(step.section).toLowerCase());
}

export function advance(previous: Progress | null, step: CommandStep): Progress {
  const total = Math.max(step.total ?? previous?.total ?? 0, step.index);
  return { done: step.index, total, label: stepLabel(step) };
}
