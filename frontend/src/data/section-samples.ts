import type { Section, SectionType } from "@/types/sections";

const photo = (file: string, alt: string) => ({
  src: `/images/library/${file}`,
  alt,
});

const icon = (name: string) => ({ src: `/icons/${name}.svg`, alt: "" });

const NAV = [
  { label: "About", href: "#about" },
  { label: "Benefits", href: "#benefits" },
  { label: "Services", href: "#services" },
  { label: "How it works", href: "#process" },
  { label: "Gallery", href: "#gallery" },
  { label: "Pricing", href: "#pricing" },
  { label: "FAQ", href: "#faq" },
  { label: "Contact", href: "#contact" },
];

const SAMPLES: { [T in SectionType]: Extract<Section, { type: T }> } = {
  header: {
    type: "header",
    name: "Marlow & Fern",
    icon: icon("croissant"),
    links: NAV,
    button: { label: "Order for collection", href: "#" },
  },

  footer: {
    type: "footer",
    name: "Marlow & Fern",
    icon: icon("croissant"),
    links: NAV,
    tagline: "A neighbourhood bakery in Chorlton, baking through the night.",
  },

  hero: {
    type: "hero",
    headline: "Bread worth the early start",
    subhead:
      "A neighbourhood bakery in Chorlton, milling our own flour and baking through the night so the first loaves are out by seven.",
    image: photo(
      "bakery-3082785.jpg",
      "Fresh sourdough loaves cooling on a rack",
    ),
    button: { label: "Order for collection", href: "#" },
  },

  about: {
    type: "about",
    eyebrow: "Since 2014",
    heading: "Two ovens, one street, eleven years",
    body: [
      "We started with a single deck oven in a converted garage and a standing order for forty loaves a week. The queue outside on Saturdays is the only marketing we have ever done.",
      "Everything is mixed, shaped and baked on site. We mill Maris Widgeon wheat from a farm in Cheshire twice a week, which is why the crumb tastes different in August than it does in February.",
    ],
    image: photo(
      "bakery-7966005.jpg",
      "Baker shaping dough on a floured bench",
    ),
    button: { label: "Read our story", href: "#" },
  },

  benefits: {
    type: "benefits",
    heading: "Why the queue is worth it",
    subhead:
      "Small batches, long ferments and no shortcuts -- the things that make the difference are the ones that take time.",
    items: [
      {
        icon: icon("sprout"),
        title: "Milled on site",
        caption:
          "Whole grain stone-milled twice weekly, so the flour is days old rather than months.",
      },
      {
        icon: icon("clock"),
        title: "36-hour ferment",
        caption:
          "A slow rise develops the flavour and makes the bread easier to digest.",
      },
      {
        icon: icon("leaf"),
        title: "Nothing wasted",
        caption:
          "Yesterday's loaves become our croutons, breadcrumbs and Tuesday soup.",
      },
    ],
  },

  services: {
    type: "services",
    heading: "What comes out of the ovens",
    subhead: "Daily bakes, plus the things we make to order.",
    items: [
      {
        title: "Daily bread",
        caption:
          "Sourdough, seeded rye and a soft white tin, baked twice a day and sold until they run out.",
        image: photo("bakery-4515023.jpg", "Loaves of bread on wooden shelves"),
        button: { label: "See today's bakes", href: "#" },
      },
      {
        title: "Pastry counter",
        caption:
          "Laminated by hand each morning -- croissants, pain aux raisins and a rotating Friday special.",
        image: photo("bakery-8426687.jpg", "Tray of freshly baked croissants"),
        button: { label: "View the counter", href: "#" },
      },
      {
        title: "Celebration cakes",
        caption:
          "Made to order with a week's notice. Tell us the occasion and we will suggest something.",
        image: photo("bakery-10481790.jpg", "Decorated celebration cake"),
        button: { label: "Enquire about a cake", href: "#" },
      },
    ],
  },

  process: {
    type: "process",
    heading: "How an order works",
    subhead: "Three steps, and one of them is just waiting for the oven.",
    items: [
      {
        icon: icon("search"),
        title: "Choose your bake",
        caption:
          "Browse what is on this week. Everything is listed with its flour and ferment time.",
      },
      {
        icon: icon("calendar-check"),
        title: "Pick a day",
        caption:
          "Order by 6pm for collection the next morning, or reserve a slot up to two weeks out.",
      },
      {
        icon: icon("hand-platter"),
        title: "Collect it warm",
        caption:
          "We bag it when you arrive rather than the night before, so the crust is still crackling.",
      },
    ],
  },

  stats: {
    type: "stats",
    heading: "Eleven years of early mornings",
    items: [
      {
        value: "11 yrs",
        label: "On Beech Road",
        caption: "Same shop, same ovens.",
      },
      {
        value: "480",
        label: "Loaves a day",
        caption: "Every one shaped by hand.",
      },
      { value: "4.9", label: "Google rating", caption: "From 612 reviews." },
      {
        value: "0",
        label: "Payday loans",
        caption: "We own both ovens outright.",
      },
    ],
  },

  gallery: {
    type: "gallery",
    heading: "From the bench",
    subhead: "Photographs from an ordinary week.",
    images: [
      photo("bakery-14774815.jpg", "Dough proving in linen-lined baskets"),
      photo(
        "bakery-17301616.jpg",
        "Scoring a loaf before it goes into the oven",
      ),
      photo(
        "bakery-18656839.jpg",
        "The pastry counter first thing in the morning",
      ),
      photo("bakery-19803485.jpg", "Bread cooling on steel racks"),
      photo("bakery-31132630.jpg", "A baker sliding loaves into the deck oven"),
      photo("bakery-34909337.jpg", "Flour-dusted work bench and scales"),
    ],
  },

  testimonials: {
    type: "testimonials",
    heading: "What people say on the way out",
    items: [
      {
        name: "Priya M., Chorlton",
        rating: 5,
        content:
          "I have been buying the seeded rye every Saturday for four years. It is the only bread my father, who grew up in Riga, will admit is proper.",
      },
      {
        name: "Tom H., Whalley Range",
        rating: 5,
        content:
          "Ordered a cake for my daughter's christening with about six days' notice. They asked what she was like, not what I wanted on it, and somehow got it exactly right.",
      },
      {
        name: "Dee A., Sale",
        rating: 4,
        content:
          "Sells out by noon on Sundays, which is my only complaint and also the reason it is good.",
      },
    ],
  },

  pricing: {
    type: "pricing",
    heading: "Standing orders",
    subhead: "Set it once and collect the same bake every week.",
    plans: [
      {
        name: "The Loaf",
        price: "£16",
        period: "per month",
        description: "One loaf a week, your choice on the day.",
        features: ["Any daily loaf", "Reserved until 2pm", "Pause any week"],
        button: { label: "Start a loaf order", href: "#" },
      },
      {
        name: "The Weekender",
        price: "£34",
        period: "per month",
        description: "Two loaves and two pastries, collected on Saturdays.",
        features: [
          "Two loaves weekly",
          "Two pastries weekly",
          "Reserved until 2pm",
          "First refusal on Friday specials",
        ],
        button: { label: "Start a weekender", href: "#" },
        featured: true,
      },
      {
        name: "The Table",
        price: "£72",
        period: "per month",
        description: "For households that get through a lot of bread.",
        features: [
          "Four loaves weekly",
          "Six pastries weekly",
          "10% off celebration cakes",
          "Reserved until close",
        ],
        button: { label: "Start a table order", href: "#" },
      },
    ],
  },

  team: {
    type: "team",
    heading: "Who is in at four in the morning",
    subhead: "A small team, most of whom trained here.",
    members: [
      {
        name: "Aoife Brennan",
        role: "Head baker & owner",
        photo: photo("bakery-36445212.jpg", "Aoife at the mixing bench"),
        bio: "Ran the garage oven for two years before the shop existed. Still shapes the Saturday sourdough herself.",
      },
      {
        name: "Marcus Obi",
        role: "Pastry",
        photo: photo("bakery-37290074.jpg", "Marcus laminating dough"),
        bio: "Came for a two-week placement in 2019 and has laminated every croissant since.",
      },
      {
        name: "Sofia Reyes",
        role: "Front of shop",
        photo: photo("bakery-38456849.jpg", "Sofia at the counter"),
        bio: "Knows roughly four hundred regulars by their usual order.",
      },
    ],
  },

  promotion: {
    type: "promotion",
    title: "Free pastry with your first standing order",
    description:
      "Start any weekly order before the end of the month and your first collection comes with whatever Marcus is proudest of that morning.",
    button: { label: "Claim the offer", href: "#" },
  },

  faq: {
    type: "faq",
    heading: "Questions we get at the counter",
    items: [
      {
        question: "What time do you sell out?",
        answer:
          "Usually around 1pm on weekdays and by noon at weekends. A standing order holds your bread until 2pm whatever happens.",
      },
      {
        question: "Do you do gluten-free bread?",
        answer:
          "No. We mill wheat in the same room we bake in, so we cannot honestly call anything gluten-free, and we would rather say so than hedge.",
      },
      {
        question: "How much notice do you need for a cake?",
        answer:
          "A week for most things, two if it needs more than one tier. We will tell you straight away if the date is already full.",
      },
      {
        question: "Can I pay on collection?",
        answer:
          "Yes, card or cash at the counter. Standing orders are billed monthly by direct debit.",
      },
    ],
  },

  contact: {
    type: "contact",
    heading: "Come and find us",
    description:
      "We are on Beech Road, three doors down from the post office. There is no parking outside, but plenty on Cross Road.",
    details: [
      {
        label: "Shop",
        value: "114 Beech Road, Chorlton, M21 9EG",
        icon: icon("map-pin"),
      },
      { label: "Phone", value: "0161 881 4042", icon: icon("phone") },
      {
        label: "Email",
        value: "hello@marlowandfern.co.uk",
        icon: icon("mail"),
      },
      {
        label: "Open",
        value: "Tue–Sun, 7am until sold out",
        icon: icon("clock"),
      },
    ],
    button: { label: "Get directions", href: "#" },
    image: photo("bakery-8426687.jpg", "The bakery shopfront on Beech Road"),
  },

  cta: {
    type: "cta",
    headline: "Bread is reserved, not promised",
    subhead:
      "Standing orders start at £16 a month and hold your loaf until two in the afternoon.",
    button: { label: "Start a standing order", href: "#" },
    secondary: { label: "Call the shop", href: "tel:01618814042" },
    image: photo("bakery-19803485.jpg", "Loaves cooling on steel racks"),
  },
};

export const SAMPLE_BRAND = {
  name: "Marlow & Fern",
  icon: { src: "/icons/croissant.svg", alt: "" },
  tagline: "A neighbourhood bakery in Chorlton, baking through the night.",
};

export function sampleSection<T extends SectionType>(
  type: T,
  variant?: string,
): Extract<Section, { type: T }> {
  return { ...SAMPLES[type], variant } as Extract<Section, { type: T }>;
}

export { SAMPLES as SECTION_SAMPLES };
