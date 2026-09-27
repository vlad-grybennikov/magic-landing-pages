import {
  Bitter,
  Cormorant_Garamond,
  Fraunces,
  Inter,
  Karla,
  Lato,
  Libre_Baskerville,
  Lora,
  Montserrat,
  Nunito_Sans,
  Open_Sans,
  Outfit,
  Playfair_Display,
  Poppins,
  Source_Sans_3,
  Space_Grotesk,
} from "next/font/google";
import { MANIFEST } from "@/generated/manifest";

const inter = Inter({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-inter" });
const outfit = Outfit({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-outfit" });
const playfair = Playfair_Display({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-playfair" });
const sourceSans = Source_Sans_3({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-source-sans" });
const fraunces = Fraunces({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-fraunces" });
const nunitoSans = Nunito_Sans({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-nunito-sans" });
const spaceGrotesk = Space_Grotesk({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-space-grotesk" });
const libreBaskerville = Libre_Baskerville({ subsets: ["latin"], display: "swap", preload: false, weight: ["400", "700"], variable: "--f-libre-baskerville" });
const lato = Lato({ subsets: ["latin"], display: "swap", preload: false, weight: ["400", "700"], variable: "--f-lato" });
const poppins = Poppins({ subsets: ["latin"], display: "swap", preload: false, weight: ["400", "500", "600", "700"], variable: "--f-poppins" });
const cormorant = Cormorant_Garamond({ subsets: ["latin"], display: "swap", preload: false, weight: ["400", "500", "600", "700"], variable: "--f-cormorant" });
const montserrat = Montserrat({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-montserrat" });
const bitter = Bitter({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-bitter" });
const openSans = Open_Sans({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-open-sans" });
const lora = Lora({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-lora" });
const karla = Karla({ subsets: ["latin"], display: "swap", preload: false, variable: "--f-karla" });

export const FONT_VARIABLE_CLASS = [
  inter,
  outfit,
  playfair,
  sourceSans,
  fraunces,
  nunitoSans,
  spaceGrotesk,
  libreBaskerville,
  lato,
  poppins,
  cormorant,
  montserrat,
  bitter,
  openSans,
  lora,
  karla,
]
  .map((font) => font.variable)
  .join(" ");

export interface FontPair {
  label: string;
  heading: string;
  body: string;
}

const FAMILIES: Record<string, string> = {
  "Inter": "--f-inter",
  "Outfit": "--f-outfit",
  "Playfair Display": "--f-playfair",
  "Source Sans 3": "--f-source-sans",
  "Fraunces": "--f-fraunces",
  "Nunito Sans": "--f-nunito-sans",
  "Space Grotesk": "--f-space-grotesk",
  "Libre Baskerville": "--f-libre-baskerville",
  "Lato": "--f-lato",
  "Poppins": "--f-poppins",
  "Cormorant Garamond": "--f-cormorant",
  "Montserrat": "--f-montserrat",
  "Bitter": "--f-bitter",
  "Open Sans": "--f-open-sans",
  "Lora": "--f-lora",
  "Karla": "--f-karla",
};

function family(name: string): string {
  const variable = FAMILIES[name];
  if (!variable) throw new Error(`No loaded font family called ${name}`);
  return `var(${variable})`;
}

export const FONT_PAIRS: Record<string, FontPair> = Object.fromEntries(
  Object.entries(MANIFEST.fontPairs).map(([name, pair]) => [
    name,
    {
      label:
        pair.heading === pair.body
          ? pair.heading
          : `${pair.heading} / ${pair.body}`,
      heading: family(pair.heading),
      body: family(pair.body),
    },
  ]),
);

export const FONT_PAIR_NAMES = Object.keys(FONT_PAIRS);

export const DEFAULT_FONT_PAIR: string = MANIFEST.defaultFontPair;

export function fontVars(pair?: string | null): Record<string, string> {
  const chosen = FONT_PAIRS[pair ?? ""];
  if (!chosen) return {};
  return {
    "--font-heading": `${chosen.heading}, ui-sans-serif, system-ui, sans-serif`,
    "--font-body": `${chosen.body}, ui-sans-serif, system-ui, sans-serif`,
  };
}
