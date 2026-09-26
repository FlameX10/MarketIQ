const JSZip = require('jszip');
const fs = require('fs');
const path = require('path');

const LENGTH_LIMITS = {
  type_segment_1: 30,
  type_segment_2: 35,
  type_segment_3: 50,
  tech_segment_1: 30,
  tech_segment_2: 30,
  tech_segment_3: 40,
  app_segment_1: 30,
  app_segment_2: 30,
  app_segment_3: 30,
  app_segment_4: 30,
  co1_name: 20,
  co2_name: 20,
  co3_name: 20,
  co4_name: 30,
  co5_name: 15,
  co6_name: 15,
  co7_name: 20,
  co8_name: 15,
  co9_name: 15,
  co10_name: 15,
  co1_segment_1_name: 50,
  co1_segment_2_name: 50,
  segment5_marketshare1: 30,
  segment5_marketshare2: 30,
  segment5_marketshare3: 30,
  segment5_marketshare4: 30,
  segment6_marketshare1: 30,
  segment6_marketshare2: 30,
  segment6_marketshare3: 30,
  segment6_marketshare4: 30,
  seg4_name: 30,
  seg4_sub1: 30,
  seg4_sub2: 30,
  seg4_sub3: 30,
  seg5_name: 30,
  seg5_sub1: 30,
  seg5_sub2: 30,
  seg5_sub3: 30,
  seg6_name: 30,
  seg6_sub1: 30,
  seg6_sub2: 30,
  seg6_sub3: 30,
  ch4_custom_subsection_4_1_title: 50,
};

function truncateText(text, maxLen) {
  if (!text) return text;
  const str = String(text).trim();
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 3).trim() + "...";
}

function extractCoreProductName(rawName) {
  const wordsToRemove = ["Global", "Market", "Segmentation", "Industry", "Analysis", "Overview"];
  let coreName = rawName;
  for (const word of wordsToRemove) {
    coreName = coreName.replace(new RegExp(`\\b${word}\\b`, 'gi'), '');
  }
  coreName = coreName.replace(/\s+/g, ' ').trim();
  if (!coreName) {
    const parts = rawName.split(/\s+/);
    coreName = parts.length > 1 ? parts.slice(0, 2).join(' ') : rawName;
  }
  return coreName.trim();
}

function sanitizeFilename(name) {
  const safe = name.replace(/[^a-zA-Z0-9\s\-_]/g, '_');
  return safe.trim().replace(/\s+/g, '_');
}

function getFallbackContent(marketName, marketInput) {
  const core = extractCoreProductName(marketName);
  const segments = (marketInput && marketInput.parsed_segments) || [];

  function segSubs(keywords, n) {
    for (const seg of segments) {
      const nl = seg.name.toLowerCase();
      if (keywords.some(k => nl.includes(k)) && seg.sub_segments && seg.sub_segments.length > 0) {
        return seg.sub_segments.slice(0, n);
      }
    }
    return [];
  }
  function pick(subs, idx, fallback) {
    return (subs && subs.length > idx) ? subs[idx] : fallback;
  }
  function segName(keywords, fallback) {
    const seg = segments.find(s => keywords.some(k => s.name.toLowerCase().includes(k)));
    return seg ? seg.name : fallback;
  }

  const typeSubs  = segSubs(['type', 'product', 'form', 'grade'], 3);
  const techSubs  = segSubs(['tech', 'process', 'method'], 3);
  const appSubs   = segSubs(['app', 'end-use', 'use'], 4);
  const euSubs    = segSubs(['end user', 'user', 'consumer'], 3);
  const euName    = segName(['end user', 'user', 'consumer'], 'End User');
  const distSubs  = segSubs(['distribut', 'channel', 'sales'], 4);
  const distName  = segName(['distribut', 'channel', 'sales'], 'Distribution Channel');
  const matSubs   = segSubs(['material', 'raw'], 4);
  const matName   = segName(['material', 'raw'], 'Material');

  return {
    type_segment_1: pick(typeSubs, 0, `${core} Standard Grade`),
    type_segment_2: pick(typeSubs, 1, `${core} Premium Grade`),
    type_segment_3: pick(typeSubs, 2, `${core} Specialized Grade`),
    tech_segment_1: pick(techSubs, 0, 'Advanced Automated Processing'),
    tech_segment_2: pick(techSubs, 1, 'NextGen Manufacturing'),
    tech_segment_3: pick(techSubs, 2, 'High-Efficiency Production'),
    app_segment_1: pick(appSubs, 0, 'Industrial Applications'),
    app_segment_2: pick(appSubs, 1, 'Commercial Sector'),
    app_segment_3: pick(appSubs, 2, 'Residential Sector'),
    app_segment_4: pick(appSubs, 3, pick(appSubs, 0, 'Specialty Applications')),
    co1_name: `Global ${core} Leaders`,
    co2_name: `${core} Innovations Inc`,
    co3_name: `Apex ${core} Solutions`,
    co4_name: `Prime ${core} Corp`,
    co5_name: `Vanguard ${core}`,
    co6_name: `United ${core}`,
    co7_name: `International ${core}`,
    co8_name: `Strategic ${core}`,
    co9_name: `Pioneer ${core}`,
    co10_name: `Global ${core} Enterprise`,
    co1_segment_1_name: `Core ${core} Products`,
    co1_segment_2_name: `${core} Services & Accessories`,
    seg4_name: euName,
    seg4_sub1: pick(euSubs, 0, 'Industrial End Users'),
    seg4_sub2: pick(euSubs, 1, 'Commercial End Users'),
    seg4_sub3: pick(euSubs, 2, 'Individual Consumers'),
    seg5_name: distName,
    seg5_sub1: pick(distSubs, 0, 'Direct Enterprise Sales'),
    seg5_sub2: pick(distSubs, 1, 'Distributor Network'),
    seg5_sub3: pick(distSubs, 2, 'Online E-Commerce'),
    segment5_marketshare1: pick(distSubs, 0, 'Direct Enterprise Sales'),
    segment5_marketshare2: pick(distSubs, 1, 'Distributor Network'),
    segment5_marketshare3: pick(distSubs, 2, 'Online Channels'),
    segment5_marketshare4: pick(distSubs, 3, pick(distSubs, 0, 'Retail')),
    seg6_name: matName,
    seg6_sub1: pick(matSubs, 0, 'Premium Material'),
    seg6_sub2: pick(matSubs, 1, 'Standard Material'),
    seg6_sub3: pick(matSubs, 2, 'Composite Material'),
    segment6_marketshare1: pick(matSubs, 0, 'Premium Material'),
    segment6_marketshare2: pick(matSubs, 1, 'Standard Material'),
    segment6_marketshare3: pick(matSubs, 2, 'Composite Material'),
    segment6_marketshare4: pick(matSubs, 3, pick(matSubs, 0, 'Eco-friendly Material')),
    ch4_custom_subsection_4_1_title: `Strategic Analysis of ${core} Market Opportunities`,
  };
}

function validatePayload(payloadDict) {
  const genericPatterns = [
    [/\b(Type|Tech|App)\s+\d+\b/i, "Generic segment placeholder (e.g. Type 1, Tech 2, App 3)"],
    [/\bSegment\s+[456]\b/i, "Generic dimension name (e.g. Segment 4, Segment 5, Segment 6)"],
    [/\bSub-Segment\s*\d*\b/i, "Generic sub-segment label"],
    [/\bClient Requirement\s*\d*(\.\d+)?\b/i, "Generic client requirement title"],
    [/\bFEATURED COMPANY\b/i, "Generic company placeholder"],
    [/\bCompetitor\s+\d+\b/i, "Generic competitor placeholder"],
    [/www\.FEATURED\s*COMPANY\.com/i, "Fake company URL"],
  ];

  const errors = [];
  for (const [key, val] of Object.entries(payloadDict)) {
    if (!val || typeof val !== 'string') continue;
    for (const [pattern, desc] of genericPatterns) {
      if (pattern.test(val)) {
        errors.append ? errors.append(`${key}: ${val}`) : errors.push(`Unresolved placeholder in '${key}': '${val}' (${desc})`);
      }
    }
  }

  return { isValid: errors.length === 0, errors };
}

async function parseDocxBuffer(buffer) {
  const zip = await JSZip.loadAsync(buffer);
  const documentXml = await zip.file("word/document.xml").async("text");
  
  // Extract all text inside <w:t> elements
  const textMatches = documentXml.match(/<w:t[^>]*>(.*?)<\/w:t>/g) || [];
  const fullText = textMatches.map(m => m.replace(/<[^>]+>/g, '')).join(' ');

  let marketName = "Market Research Report";
  const nameMatch = fullText.match(/(?:Global\s+)?([A-Za-z0-9\s\-–]+?)\s+Market\s+Segmentation/i);
  if (nameMatch && nameMatch[1]) {
    marketName = extractCoreProductName(nameMatch[1]);
  } else {
    const titleMatch = fullText.match(/Global\s+([A-Za-z0-9\s\-–]+?)\s+Market/i);
    if (titleMatch && titleMatch[1]) {
      marketName = extractCoreProductName(titleMatch[1]);
    }
  }

  // Multi-pattern Segment Parser
  const parsedSegments = [];
  const segMap = {};

  // Pattern A: Inline lines like "1. Type: Porcelain, Glazed..." or "By Type: ..."
  const inlineLines = fullText.match(/(?:By\s+|\d+[\.\)]\s*)?([A-Za-z0-9\s/&\-]+?)\s*:\s*([^.\n]+)/g) || [];
  for (const line of inlineLines) {
    const parts = line.split(':');
    if (parts.length >= 2) {
      const header = parts[0].replace(/^(?:By\s+|\d+[\.\)]\s*)/i, '').trim();
      const vals = parts[1].split(/[,;\n]/).map(s => s.trim()).filter(Boolean);
      const hLower = header.toLowerCase();
      if (!hLower.includes('global') && !hLower.includes('market') && !hLower.includes('player') && !hLower.includes('custom') && vals.length > 0) {
        segMap[header] = vals;
      }
    }
  }

  // Convert segMap to parsedSegments array
  for (const [name, subs] of Object.entries(segMap)) {
    parsedSegments.push({ name, sub_segments: subs });
  }

  // Key Players
  const players = [];
  const playerSection = fullText.match(/(?:Key Players|Top Companies|Competitive Landscape)[^:]*:\s*([^.\n]+)/i);
  if (playerSection && playerSection[1]) {
    const list = playerSection[1].split(/,|\n/).map(p => p.trim().replace(/^[-•*\d+.]\s*/, '')).filter(Boolean);
    players.push(...list);
  }

  // Custom sections
  const customSections = [];
  const customMatch = fullText.match(/(?:Custom Requirements|Client Requirements)[^:]*:\s*([^.]+)/i);
  if (customMatch && customMatch[1]) {
    const reqs = customMatch[1].split(/;|\n|\d+\./).map(r => r.trim().replace(/^[-•*\d+.]\s*/, '')).filter(r => r.length > 5);
    for (const r of reqs) {
      customSections.push({ title: r });
    }
  }

  return {
    market_name: marketName,
    market_name_upper: marketName.toUpperCase(),
    market_name_title: marketName,
    parsed_segments: parsedSegments,
    parsed_players: players,
    custom_sections: customSections,
    report_geography: "Global",
    company_name: "NextGen Intelligence Stats and Consulting LLP",
    base_year: "2024",
    forecast_start_year: "2025",
    forecast_end_year: "2035",
    history_start_year: "2020",
    cover_title_truncated: marketName.length > 20,
  };
}

const KNOWN_COMPANY_MAPS = {
  "ceramic tiles": [
    "CERAMICA FLAMINIA",
    "Marazzi Group",
    "Concorde Group",
    "Gres Ceramica",
    "Ariafloor",
    "Baldassarre",
    "Iris Ceramica",
    "Vega",
    "Daltile",
    "Florida Tile",
  ]
};

function buildPayload(aiContent, marketInput) {
  const core = marketInput.market_name;
  const segments = marketInput.parsed_segments || [];
  const ai = aiContent || {};

  function val(key, fallback = "") {
    return (ai[key] && String(ai[key]).trim()) ? String(ai[key]).trim() : fallback;
  }

  function getSub(aiKey, segObj, idx, fallback) {
    if (aiKey && ai[aiKey]) {
      const aiVal = String(ai[aiKey]).trim();
      const isGeneric = /type [123]|tech [123]|app [1234]/i.test(aiVal);
      if (aiVal && (!isGeneric || !segObj)) return aiVal;
    }
    if (segObj && segObj.sub_segments && segObj.sub_segments.length > idx) {
      return segObj.sub_segments[idx];
    }
    return fallback;
  }

  let typeSeg = null, techSeg = null, appSeg = null, endUserSeg = null, distSeg = null, matSeg = null;
  const assigned = new Set();

  for (const seg of segments) {
    const nameLower = seg.name.toLowerCase();
    if (!appSeg && (nameLower.includes('app') || nameLower.includes('end-use') || nameLower.includes('use') || nameLower.includes('application'))) {
      appSeg = seg;
      assigned.add(seg.name);
    } else if (!typeSeg && (nameLower.includes('type') || nameLower.includes('product') || nameLower.includes('form') || nameLower.includes('grade'))) {
      typeSeg = seg;
      assigned.add(seg.name);
    } else if (!techSeg && (nameLower.includes('tech') || nameLower.includes('process') || nameLower.includes('method') || nameLower.includes('manufacturing'))) {
      techSeg = seg;
      assigned.add(seg.name);
    } else if (!endUserSeg && (nameLower.includes('end user') || nameLower.includes('user') || nameLower.includes('consumer'))) {
      endUserSeg = seg;
      assigned.add(seg.name);
    } else if (!distSeg && (nameLower.includes('distribut') || nameLower.includes('channel') || nameLower.includes('sales'))) {
      distSeg = seg;
      assigned.add(seg.name);
    } else if (!matSeg && (nameLower.includes('material') || nameLower.includes('wood') || nameLower.includes('raw'))) {
      matSeg = seg;
      assigned.add(seg.name);
    }
  }

  const unassignedSegs = segments.filter(s => !assigned.has(s.name));
  const slots = [
    ["typeSeg", typeSeg],
    ["techSeg", techSeg],
    ["appSeg", appSeg],
    ["endUserSeg", endUserSeg],
    ["distSeg", distSeg],
    ["matSeg", matSeg],
  ];

  const resolved = {};
  for (const [slotName, currentVal] of slots) {
    if (!currentVal && unassignedSegs.length > 0) {
      resolved[slotName] = unassignedSegs.shift();
    } else {
      resolved[slotName] = currentVal;
    }
  }

  typeSeg = resolved["typeSeg"];
  techSeg = resolved["techSeg"];
  appSeg = resolved["appSeg"];
  endUserSeg = resolved["endUserSeg"];
  distSeg = resolved["distSeg"];
  matSeg = resolved["matSeg"];

  const payload = {
    "{{market_name}}": marketInput.market_name,
    "{{market_name_upper}}": marketInput.market_name_upper,
    "{{MARKET_NAME_UPPER}}": marketInput.market_name_upper,
    "{{report_geography}}": marketInput.report_geography,
    "{{company_name}}": marketInput.company_name,
    "{{base_year}}": marketInput.base_year,
    "{{forecast_start_year}}": marketInput.forecast_start_year,
    "{{forecast_end_year}}": marketInput.forecast_end_year,
    "{{history_start_year}}": marketInput.history_start_year,
    "{{co1_name_upper}}": val("co1_name", "Featured Company").toUpperCase(),
    "{{co2_name}}": val("co2_name", "Competitor 2"),
    "{{co3_name}}": val("co3_name", "Competitor 3"),
    "{{co4_name}}": val("co4_name", "Competitor 4"),
    "{{co5_name}}": val("co5_name", "Competitor 5"),
    "{{co6_name}}": val("co6_name", "Competitor 6"),
    "{{co7_name}}": val("co7_name", "Competitor 7"),
    "{{co8_name}}": val("co8_name", "Competitor 8"),
    "{{co9_name}}": val("co9_name", "Competitor 9"),
    "{{co10_name}}": val("co10_name", "Competitor 10"),
    "{{CO1_NAME}}": val("co1_name", "Featured Company").toUpperCase(),
    "{{CO2_NAME}}": val("co2_name", "Competitor 2").toUpperCase(),
    "{{CO3_NAME}}": val("co3_name", "Competitor 3").toUpperCase(),
    "{{CO4_NAME}}": val("co4_name", "Competitor 4").toUpperCase(),
    "{{CO5_NAME}}": val("co5_name", "Competitor 5").toUpperCase(),
    "{{CO6_NAME}}": val("co6_name", "Competitor 6").toUpperCase(),
    "{{CO7_NAME}}": val("co7_name", "Competitor 7").toUpperCase(),
    "{{CO8_NAME}}": val("co8_name", "Competitor 8").toUpperCase(),
    "{{CO9_NAME}}": val("co9_name", "Competitor 9").toUpperCase(),
    "{{CO10_NAME}}": val("co10_name", "Competitor 10").toUpperCase(),
    "{{co1_seg1_name}}": val("co1_segment_1_name", `${core} Segment 1`),
    "{{co1_seg2_name}}": val("co1_segment_2_name", `${core} Segment 2`),
    "{{segment5_marketshare1}}": val("segment5_marketshare1", "Sub-Segment 1"),
    "{{segment5_marketshare2}}": val("segment5_marketshare2", "Sub-Segment 2"),
    "{{segment5_marketshare3}}": val("segment5_marketshare3", "Sub-Segment 3"),
    "{{segment5_marketshare4}}": val("segment5_marketshare4", "Sub-Segment 4"),
    "{{segment6_marketshare1}}": val("segment6_marketshare1", "Sub-Segment 1"),
    "{{segment6_marketshare2}}": val("segment6_marketshare2", "Sub-Segment 2"),
    "{{segment6_marketshare3}}": val("segment6_marketshare3", "Sub-Segment 3"),
    "{{segment6_marketshare4}}": val("segment6_marketshare4", "Sub-Segment 4"),
  };

  payload["{{type_segment_1}}"] = getSub('type_segment_1', typeSeg, 0, `${core} Type 1`);
  payload["{{type_segment_2}}"] = getSub('type_segment_2', typeSeg, 1, `${core} Type 2`);
  payload["{{type_segment_3}}"] = getSub('type_segment_3', typeSeg, 2, `${core} Type 3`);

  payload["{{tech_segment_1}}"] = getSub('tech_segment_1', techSeg, 0, `${core} Tech 1`);
  payload["{{tech_segment_2}}"] = getSub('tech_segment_2', techSeg, 1, `${core} Tech 2`);
  payload["{{tech_segment_3}}"] = getSub('tech_segment_3', techSeg, 2, `${core} Tech 3`);

  payload["{{app_segment_1}}"] = getSub('app_segment_1', appSeg, 0, `${core} App 1`);
  payload["{{app_segment_2}}"] = getSub('app_segment_2', appSeg, 1, `${core} App 2`);
  payload["{{app_segment_3}}"] = getSub('app_segment_3', appSeg, 2, `${core} App 3`);
  payload["{{app_segment_4}}"] = getSub('app_segment_4', appSeg, 3, getSub('app_segment_1', appSeg, 0, `${core} App 4`));

  const seg4Name = endUserSeg ? endUserSeg.name : val('seg4_name', 'End User');
  payload["{{seg4_name}}"] = seg4Name;
  payload["{{seg4_sub1}}"] = getSub('seg4_sub1', endUserSeg, 0, `${seg4Name} 1`);
  payload["{{seg4_sub2}}"] = getSub('seg4_sub2', endUserSeg, 1, `${seg4Name} 2`);
  payload["{{seg4_sub3}}"] = getSub('seg4_sub3', endUserSeg, 2, `${seg4Name} 3`);

  const seg5Name = distSeg ? distSeg.name : val('seg5_name', 'Distribution Channel');
  payload["{{seg5_name}}"] = seg5Name;
  payload["{{seg5_sub1}}"] = getSub('seg5_sub1', distSeg, 0, `${seg5Name} 1`);
  payload["{{seg5_sub2}}"] = getSub('seg5_sub2', distSeg, 1, `${seg5Name} 2`);
  payload["{{seg5_sub3}}"] = getSub('seg5_sub3', distSeg, 2, `${seg5Name} 3`);
  payload["{{segment5_marketshare1}}"] = getSub('segment5_marketshare1', distSeg, 0, `${seg5Name} 1`);
  payload["{{segment5_marketshare2}}"] = getSub('segment5_marketshare2', distSeg, 1, `${seg5Name} 2`);
  payload["{{segment5_marketshare3}}"] = getSub('segment5_marketshare3', distSeg, 2, `${seg5Name} 3`);
  payload["{{segment5_marketshare4}}"] = getSub('segment5_marketshare4', distSeg, 3, getSub('segment5_marketshare1', distSeg, 0, `${seg5Name} 4`));

  const seg6Name = matSeg ? matSeg.name : val('seg6_name', 'Material');
  payload["{{seg6_name}}"] = seg6Name;
  payload["{{seg6_sub1}}"] = getSub('seg6_sub1', matSeg, 0, `${seg6Name} 1`);
  payload["{{seg6_sub2}}"] = getSub('seg6_sub2', matSeg, 1, `${seg6Name} 2`);
  payload["{{seg6_sub3}}"] = getSub('seg6_sub3', matSeg, 2, `${seg6Name} 3`);
  payload["{{segment6_marketshare1}}"] = getSub('segment6_marketshare1', matSeg, 0, `${seg6Name} 1`);
  payload["{{segment6_marketshare2}}"] = getSub('segment6_marketshare2', matSeg, 1, `${seg6Name} 2`);
  payload["{{segment6_marketshare3}}"] = getSub('segment6_marketshare3', matSeg, 2, `${seg6Name} 3`);
  payload["{{segment6_marketshare4}}"] = getSub('segment6_marketshare4', matSeg, 3, getSub('segment6_marketshare1', matSeg, 0, `${seg6Name} 4`));

  const customReqs = marketInput.custom_sections || [];
  for (let i = 1; i <= 4; i++) {
    const key = `{{ch4_custom_section_${i}_title}}`;
    if (customReqs.length >= i) {
      payload[key] = customReqs[i - 1].title || customReqs[i - 1];
    } else {
      payload[key] = `Client Requirement ${i}`;
    }
  }

  payload["{{ch4_custom_subsection_4_1_title}}"] = val(
    "ch4_custom_subsection_4_1_title", "Client Requirement 4.1"
  );

  return payload;
}

async function renderReportDocx(templateBuffer, placeholderDict, adjustCoverTitle) {
  const zip = await JSZip.loadAsync(templateBuffer);
  
  const files = Object.keys(zip.files);
  for (const filename of files) {
    if (filename.endsWith('.xml') || filename.endsWith('.rels')) {
      let content = await zip.file(filename).async("text");

      const escapedDict = {};
      for (const [key, val] of Object.entries(placeholderDict)) {
        escapedDict[key] = String(val)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&apos;');
      }

      // Pass 1: Literal replacement
      for (const [key, escapedVal] of Object.entries(escapedDict)) {
        if (content.includes(key)) {
          content = content.split(key).join(escapedVal);
        }
      }

      // Pass 2: Character-level split XML tag matching
      const tagPattern = "(?:<[^>]+>)*\\s*";
      for (const [key, escapedVal] of Object.entries(escapedDict)) {
        const rawKey = key.replace(/^\{\{|\}\}$/g, "").trim();
        if (!rawKey) continue;

        let patternStr = "\\{\\{\\s*";
        for (const ch of rawKey) {
          patternStr += ch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + tagPattern;
        }
        patternStr += "\\}\\}";

        const regex = new RegExp(patternStr, "gi");
        content = content.replace(regex, escapedVal);
      }

      // Pass 3: General split XML tag matching regex
      const splitRegex = /\{\{(?:<[^>]+>|[^}])*?\}\}/g;
      content = content.replace(splitRegex, (match) => {
        const cleanKey = "{{" + match.replace(/<[^>]+>/g, "").replace(/^\{\{|\}\}$/g, "").trim() + "}}";
        return escapedDict[cleanKey] !== undefined ? escapedDict[cleanKey] : "";
      });

      // Pass 4: Clean remaining unreplaced {{...}} placeholders
      content = content.replace(/\{\{[^}]+\}\}/g, "");

      if (adjustCoverTitle && filename === 'word/document.xml') {
        content = content.replace(/w:sz w:val="88"/g, 'w:sz w:val="58"');
      }

      zip.file(filename, content);
    }
  }

  return await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}

function getHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Content-Type": "application/json",
  };
}

exports.handler = async (event, context) => {
  const httpMethod = event.httpMethod || "GET";

  if (httpMethod === "OPTIONS") {
    return { statusCode: 200, headers: getHeaders(), body: "" };
  }

  const rootDir = path.resolve(__dirname, '..', '..');

  if (httpMethod === "GET") {
    let samples = [];
    try {
      const files = fs.readdirSync(rootDir);
      samples = files.filter(f => f.endsWith('.docx') && !f.startsWith('~$') && !f.toLowerCase().includes('template'));
    } catch (e) {
      samples = ["Global_BESS_Market_Segmentation.docx", "Global_Screw_Market_Segmentation.docx", "Global_Soda_Market_Segmentation.docx", "Sample_Green Methanol Market.docx"];
    }

    return {
      statusCode: 200,
      headers: getHeaders(),
      body: JSON.stringify({
        status: "online",
        service: "MarketIQ Report Generator API",
        samples: samples
      })
    };
  }

  if (httpMethod !== "POST") {
    return { statusCode: 405, headers: getHeaders(), body: JSON.stringify({ error: "Method not allowed" }) };
  }

  try {
    let bodyData = {};
    if (event.body) {
      const raw = event.isBase64Encoded ? Buffer.from(event.body, 'base64').toString('utf8') : event.body;
      bodyData = JSON.parse(raw);
    }

    const { file_data, sample_name, use_api, api_key } = bodyData;

    let inputBuffer = null;
    if (file_data) {
      inputBuffer = Buffer.from(file_data, 'base64');
    } else if (sample_name) {
      const samplePath = path.join(rootDir, sample_name);
      if (fs.existsSync(samplePath)) {
        inputBuffer = fs.readFileSync(samplePath);
      } else {
        return { statusCode: 404, headers: getHeaders(), body: JSON.stringify({ error: `Sample file '${sample_name}' not found` }) };
      }
    } else {
      return { statusCode: 400, headers: getHeaders(), body: JSON.stringify({ error: "No file_data or sample_name provided" }) };
    }

    // Step 1: Parse input docx
    const marketInput = await parseDocxBuffer(inputBuffer);

    // Step 2: AI Generation or Fallback
    let aiContent = null;
    const keyToUse = api_key || process.env.OPENROUTER_API_KEY;

    if (use_api !== false && keyToUse) {
      try {
        let segCtx = "";
        if (marketInput.parsed_segments && marketInput.parsed_segments.length > 0) {
          segCtx = "\nExtracted input segmentations from document:\n" + marketInput.parsed_segments.map(s => `- ${s.name}: ${(s.sub_segments || []).join(', ')}`).join('\n');
        }
        const prompt = `Generate market report content for ${marketInput.market_name_title}.${segCtx}\nReturn ONLY valid JSON format mapping these exact input segmentations to the fields. Do NOT invent generic segment categories.`;
        const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${keyToUse}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            model: process.env.MODEL || "nvidia/nemotron-3-nano-30b-a3b:free",
            messages: [{ role: "user", content: prompt }]
          })
        });
        if (res.ok) {
          const json = await res.json();
          const contentStr = json.choices[0].message.content;
          aiContent = JSON.parse(contentStr.replace(/```json|```/g, '').trim());
        }
      } catch (e) {
        console.log("AI API call failed, using fallback content:", e.message);
      }
    }

    if (!aiContent) {
      aiContent = getFallbackContent(marketInput.market_name, marketInput);
    }

    // Step 3: Build payload
    const payload = buildPayload(aiContent, marketInput);

    // Validate payload before rendering
    const validation = validatePayload(payload);
    if (!validation.isValid) {
      console.warn("Payload validation warnings/errors:", validation.errors);
    }

    // Step 4: Render Template DOCX
    let templatePath = path.join(rootDir, "full_market_report_template_updated.docx");
    if (!fs.existsSync(templatePath)) {
      templatePath = path.join(rootDir, "templates", "master_template_v1.docx");
    }

    const templateBuffer = fs.readFileSync(templatePath);
    const outputBuffer = await renderReportDocx(templateBuffer, payload, marketInput.cover_title_truncated);

    const docxB64 = outputBuffer.toString('base64');
    const safeName = sanitizeFilename(marketInput.market_name);
    const downloadFilename = `report_${safeName}_${Date.now()}.docx`;

    const auditData = {
      market_name: marketInput.market_name,
      market_name_upper: marketInput.market_name_upper,
      generated_at: new Date().toISOString(),
      api_model: process.env.MODEL || "nvidia/nemotron-3-nano-30b-a3b:free",
      ai_content: aiContent,
      payload: payload,
    };

    return {
      statusCode: 200,
      headers: getHeaders(),
      body: JSON.stringify({
        success: true,
        market_name: marketInput.market_name,
        filename: downloadFilename,
        docx_base64: docxB64,
        audit_json: auditData
      })
    };

  } catch (err) {
    return {
      statusCode: 500,
      headers: getHeaders(),
      body: JSON.stringify({ error: err.message, stack: err.stack })
    };
  }
};

module.exports = {
  handler: exports.handler,
  parseDocxBuffer,
  buildPayload,
  getFallbackContent,
  validatePayload,
};
