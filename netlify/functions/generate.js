const JSZip = require('jszip');
const fs = require('fs');
const path = require('path');

const rootDir = process.cwd();

function loadConfig() {
  const configPath = path.join(rootDir, 'config.json');
  if (fs.existsSync(configPath)) {
    return JSON.parse(fs.readFileSync(configPath, 'utf8'));
  }
  return {
    template_file: 'full_market_report_template_updated.docx',
    model: 'nvidia/nemotron-3-nano-30b-a3b:free',
    cache_ttl_hours: 24,
  };
}

const config = loadConfig();

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
  return str.slice(0, maxLen - 3).trim() + '...';
}

function extractCoreProductName(rawName) {
  const wordsToRemove = ['Global', 'Market', 'Segmentation', 'Industry', 'Analysis', 'Overview'];
  let coreName = rawName;
  for (const word of wordsToRemove) {
    coreName = coreName.replace(new RegExp('\\b' + word + '\\b', 'gi'), '');
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
  const core = marketName;
  return {
    type_segment_1: core + ' Type 1',
    type_segment_2: core + ' Type 2',
    type_segment_3: core + ' Type 3',
    tech_segment_1: core + ' Tech 1',
    tech_segment_2: core + ' Tech 2',
    tech_segment_3: core + ' Tech 3',
    app_segment_1: core + ' App 1',
    app_segment_2: core + ' App 2',
    app_segment_3: core + ' App 3',
    app_segment_4: core + ' App 4',
    co1_name: 'Featured Company',
    co2_name: 'Competitor 2',
    co3_name: 'Competitor 3',
    co4_name: 'Competitor 4',
    co5_name: 'Co5',
    co6_name: 'Co6',
    co7_name: 'Competitor 7',
    co8_name: 'Co8',
    co9_name: 'Co9',
    co10_name: 'Co10',
    co1_segment_1_name: core + ' Segment 1',
    co1_segment_2_name: core + ' Segment 2',
    segment5_marketshare1: 'Sub-Segment 1',
    segment5_marketshare2: 'Sub-Segment 2',
    segment5_marketshare3: 'Sub-Segment 3',
    segment5_marketshare4: 'Sub-Segment 4',
    segment6_marketshare1: 'Sub-Segment 1',
    segment6_marketshare2: 'Sub-Segment 2',
    segment6_marketshare3: 'Sub-Segment 3',
    segment6_marketshare4: 'Sub-Segment 4',
    seg4_name: core + ' Segment 4',
    seg4_sub1: 'Sub-Segment 1',
    seg4_sub2: 'Sub-Segment 2',
    seg4_sub3: 'Sub-Segment 3',
    seg5_name: core + ' Segment 5',
    seg5_sub1: 'Sub-Segment 1',
    seg5_sub2: 'Sub-Segment 2',
    seg5_sub3: 'Sub-Segment 3',
    seg6_name: core + ' Segment 6',
    seg6_sub1: 'Sub-Segment 1',
    seg6_sub2: 'Sub-Segment 2',
    seg6_sub3: 'Sub-Segment 3',
    ch4_custom_subsection_4_1_title: 'Client Requirement 4.1',
  };
}

function validatePayload(payloadDict) {
  const genericPatterns = [
    [/\b(Type|Tech|App)\s+\d+\b/i, 'Generic segment placeholder (e.g. Type 1, Tech 2, App 3)'],
    [/\bSegment\s+[456]\b/i, 'Generic dimension name (e.g. Segment 4, Segment 5, Segment 6)'],
    [/\bSub-Segment\s*\d*\b/i, 'Generic sub-segment label'],
    [/\bClient Requirement\s*\d*(\.\d+)?\b/i, 'Generic client requirement title'],
    [/\bFEATURED COMPANY\b/i, 'Generic company placeholder'],
    [/\bCompetitor\s+\d+\b/i, 'Generic competitor placeholder'],
    [/www\.FEATURED\s*COMPANY\.com/i, 'Fake company URL'],
  ];

  const errors = [];
  for (const [key, val] of Object.entries(payloadDict)) {
    if (!val || typeof val !== 'string') continue;
    for (const [pattern, desc] of genericPatterns) {
      if (pattern.test(val)) {
        errors.push(`Unresolved placeholder in '${key}': '${val}' (${desc})`);
      }
    }
  }

  return { isValid: errors.length === 0, errors };
}

function parseWpTElements(documentXml) {
  const textMatches = documentXml.match(/<w:t[^>]*>(.*?)<\/w:t>/g) || [];
  return textMatches.map(m => m.replace(/<[^>]+>/g, '')).join(' ');
}

function getStyleFromParagraphXml(pXml) {
  const styleMatch = pXml.match(/<w:pStyle[^>]*w:val="([^"]+)"/);
  return styleMatch ? styleMatch[1] : 'Normal';
}

function getParaTextFromXml(pXml) {
  const matches = pXml.match(/<w:t[^>]*>(.*?)<\/w:t>/g) || [];
  return matches.map(m => m.replace(/<[^>]+>/g, '')).join('');
}

async function parseDocxBuffer(buffer) {
  const zip = await JSZip.loadAsync(buffer);
  const documentXml = await zip.file('word/document.xml').async('text');

  const knownRegions = [
    'North America', 'Europe', 'Asia-Pacific', 'Asia Pacific',
    'South America', 'Latin America', 'Middle East & Africa',
    'Middle East and Africa', 'MEA', 'Africa', 'APAC',
  ];

  const segments = documentXml.split('</w:p>');

  let marketTitle = '';
  const segmentations = {};
  const parsedSegments = [];
  let currentSegment = null;
  let currentRegion = null;
  const regions = {};
  const parsedRegions = [];
  const parsedRegion1Countries = [];
  let keyPlayers = [];
  let inPlayersSection = false;
  let inCustomSection = false;
  const customSections = [];
  let inRegionSection = false;

  for (const seg of segments) {
    const pXml = seg + '</w:p>';
    const style = getStyleFromParagraphXml(pXml);
    const text = getParaTextFromXml(pXml).trim();
    if (!text) continue;

    if (style === 'Heading 1' && !marketTitle) {
      marketTitle = text;
      continue;
    }

    const isHeading2 = style === 'Heading 2';
    const isBySection = text.startsWith('By ');
    const isNamedSection = ['Key Players', 'Key Players:', 'Custom Requirements', 'Custom Requirement', 'Custom Requirements:'].includes(text);

    if (isNamedSection) {
      if (text.includes('Key Players')) {
        inPlayersSection = true;
        inCustomSection = false;
        inRegionSection = false;
        currentSegment = null;
        currentRegion = null;
        continue;
      }
      if (text.includes('Custom Requirements') || text.includes('Custom Requirement')) {
        inCustomSection = true;
        inPlayersSection = false;
        inRegionSection = false;
        currentSegment = null;
        currentRegion = null;
        continue;
      }
    }

    if (text === 'By Region' || text.startsWith('By Region')) {
      inRegionSection = true;
      inPlayersSection = false;
      inCustomSection = false;
      currentSegment = null;
      currentRegion = null;
      continue;
    }

    if (isHeading2 || isBySection) {
      if (text === 'By Region' || text.startsWith('By Region')) {
        inRegionSection = true;
        inPlayersSection = false;
        inCustomSection = false;
        currentSegment = null;
        currentRegion = null;
      } else if (text.startsWith('By ')) {
        const segName = text.replace('By ', '').trim().replace(':', '');
        currentSegment = segName;
        if (!segmentations[currentSegment]) {
          segmentations[currentSegment] = [];
          parsedSegments.push({ name: currentSegment, sub_segments: [] });
        }
        inPlayersSection = false;
        inCustomSection = false;
        inRegionSection = false;
      } else if (isHeading2) {
        inPlayersSection = false;
        inCustomSection = false;
        inRegionSection = false;
        currentSegment = null;
      }
      continue;
    }

    if (inPlayersSection && text) {
      const cleaned = text.replace(/^[-•*\d+.\s]+/, '').trim();
      if (cleaned.length > 0) {
        keyPlayers.push(cleaned);
      }
      continue;
    }

    if (inCustomSection && text) {
      const cleaned = text.replace(/^[-•*\d+.\s]+/, '').trim();
      if (cleaned.length > 5) {
        customSections.push({ title: cleaned });
      }
      continue;
    }

    if (inRegionSection && text) {
      if (knownRegions.includes(text)) {
        currentRegion = text;
        if (!regions[currentRegion]) {
          regions[currentRegion] = [];
          parsedRegions.push(currentRegion);
        }
      } else if (currentRegion) {
        regions[currentRegion].push(text);
      }
      continue;
    }

    if (currentSegment && segmentations[currentSegment]) {
      const existingSubs = segmentations[currentSegment];
      if (!existingSubs.includes(text)) {
        existingSubs.push(text);
        const segObj = parsedSegments.find(s => s.name === currentSegment);
        if (segObj && !segObj.sub_segments.includes(text)) {
          segObj.sub_segments.push(text);
        }
      }
    }
  }

  let marketName = 'Market Research Report';
  const nameMatch = marketTitle.match(/(?:Global\s+)?([A-Za-z0-9\s\-–]+?)\s+Market\s+Segmentation/i);
  if (nameMatch && nameMatch[1]) {
    marketName = extractCoreProductName(nameMatch[1]);
  } else {
    const titleMatch = marketTitle.match(/Global\s+([A-Za-z0-9\s\-–]+?)\s+Market/i);
    if (titleMatch && titleMatch[1]) {
      marketName = extractCoreProductName(titleMatch[1]);
    } else {
      const base = marketTitle.replace(/[_-]/g, ' ').trim();
      marketName = extractCoreProductName(base) || 'Market Research Report';
    }
  }

  if (!marketTitle) {
    marketName = 'Market Research Report';
  }

  return {
    market_name: marketName,
    market_name_upper: marketName.toUpperCase(),
    market_name_title: marketName,
    parsed_segments: parsedSegments,
    parsed_players: keyPlayers.slice(0, 10),
    custom_sections: customSections,
    report_geography: 'Global',
    company_name: 'NextGen Intelligence Stats and Consulting LLP',
    base_year: '2024',
    forecast_start_year: '2025',
    forecast_end_year: '2035',
    history_start_year: '2020',
    cover_title_truncated: marketName.length > 20,
  };
}

const KNOWN_COMPANY_MAPS = {
  'ceramic tiles': [
    'CERAMICA FLAMINIA', 'Marazzi Group', 'Concorde Group',
    'Gres Ceramica', 'Ariafloor', 'Baldassarre',
    'Iris Ceramica', 'Vega', 'Daltile', 'Florida Tile',
  ]
};

function buildPayload(aiContent, marketInput) {
  const core = marketInput.market_name;
  const segments = marketInput.parsed_segments || [];
  const ai = aiContent || {};

  function val(key, fallback = '') {
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
      appSeg = seg; assigned.add(seg.name);
    } else if (!typeSeg && (nameLower.includes('type') || nameLower.includes('product') || nameLower.includes('form') || nameLower.includes('grade'))) {
      typeSeg = seg; assigned.add(seg.name);
    } else if (!techSeg && (nameLower.includes('tech') || nameLower.includes('process') || nameLower.includes('method') || nameLower.includes('manufacturing'))) {
      techSeg = seg; assigned.add(seg.name);
    } else if (!endUserSeg && (nameLower.includes('end user') || nameLower.includes('user') || nameLower.includes('consumer'))) {
      endUserSeg = seg; assigned.add(seg.name);
    } else if (!distSeg && (nameLower.includes('distribut') || nameLower.includes('channel') || nameLower.includes('sales'))) {
      distSeg = seg; assigned.add(seg.name);
    } else if (!matSeg && (nameLower.includes('material') || nameLower.includes('wood') || nameLower.includes('raw'))) {
      matSeg = seg; assigned.add(seg.name);
    }
  }

  const unassignedSegs = segments.filter(s => !assigned.has(s.name));
  const slots = [['typeSeg', typeSeg], ['techSeg', techSeg], ['appSeg', appSeg], ['endUserSeg', endUserSeg], ['distSeg', distSeg], ['matSeg', matSeg]];
  const resolved = {};
  for (const [slotName, currentVal] of slots) {
    if (!currentVal && unassignedSegs.length > 0) {
      resolved[slotName] = unassignedSegs.shift();
    } else {
      resolved[slotName] = currentVal;
    }
  }
  typeSeg = resolved['typeSeg']; techSeg = resolved['techSeg']; appSeg = resolved['appSeg'];
  endUserSeg = resolved['endUserSeg']; distSeg = resolved['distSeg']; matSeg = resolved['matSeg'];

  const payload = {
    '{{market_name}}': marketInput.market_name,
    '{{market_name_upper}}': marketInput.market_name_upper,
    '{{MARKET_NAME_UPPER}}': marketInput.market_name_upper,
    '{{report_geography}}': marketInput.report_geography,
    '{{company_name}}': marketInput.company_name,
    '{{base_year}}': marketInput.base_year,
    '{{forecast_start_year}}': marketInput.forecast_start_year,
    '{{forecast_end_year}}': marketInput.forecast_end_year,
    '{{history_start_year}}': marketInput.history_start_year,
    '{{co1_name_upper}}': val('co1_name', 'Featured Company').toUpperCase(),
    '{{co2_name}}': val('co2_name', 'Competitor 2'),
    '{{co3_name}}': val('co3_name', 'Competitor 3'),
    '{{co4_name}}': val('co4_name', 'Competitor 4'),
    '{{co5_name}}': val('co5_name', 'Competitor 5'),
    '{{co6_name}}': val('co6_name', 'Competitor 6'),
    '{{co7_name}}': val('co7_name', 'Competitor 7'),
    '{{co8_name}}': val('co8_name', 'Competitor 8'),
    '{{co9_name}}': val('co9_name', 'Competitor 9'),
    '{{co10_name}}': val('co10_name', 'Competitor 10'),
    '{{CO1_NAME}}': val('co1_name', 'Featured Company').toUpperCase(),
    '{{CO2_NAME}}': val('co2_name', 'Competitor 2').toUpperCase(),
    '{{CO3_NAME}}': val('co3_name', 'Competitor 3').toUpperCase(),
    '{{CO4_NAME}}': val('co4_name', 'Competitor 4').toUpperCase(),
    '{{CO5_NAME}}': val('co5_name', 'Competitor 5').toUpperCase(),
    '{{CO6_NAME}}': val('co6_name', 'Competitor 6').toUpperCase(),
    '{{CO7_NAME}}': val('co7_name', 'Competitor 7').toUpperCase(),
    '{{CO8_NAME}}': val('co8_name', 'Competitor 8').toUpperCase(),
    '{{CO9_NAME}}': val('co9_name', 'Competitor 9').toUpperCase(),
    '{{CO10_NAME}}': val('co10_name', 'Competitor 10').toUpperCase(),
    '{{co1_seg1_name}}': val('co1_segment_1_name', `${core} Segment 1`),
    '{{co1_seg2_name}}': val('co1_segment_2_name', `${core} Segment 2`),
    '{{segment5_marketshare1}}': val('segment5_marketshare1', 'Sub-Segment 1'),
    '{{segment5_marketshare2}}': val('segment5_marketshare2', 'Sub-Segment 2'),
    '{{segment5_marketshare3}}': val('segment5_marketshare3', 'Sub-Segment 3'),
    '{{segment5_marketshare4}}': val('segment5_marketshare4', 'Sub-Segment 4'),
    '{{segment6_marketshare1}}': val('segment6_marketshare1', 'Sub-Segment 1'),
    '{{segment6_marketshare2}}': val('segment6_marketshare2', 'Sub-Segment 2'),
    '{{segment6_marketshare3}}': val('segment6_marketshare3', 'Sub-Segment 3'),
    '{{segment6_marketshare4}}': val('segment6_marketshare4', 'Sub-Segment 4'),
  };

  payload['{{type_segment_1}}'] = getSub('type_segment_1', typeSeg, 0, `${core} Type 1`);
  payload['{{type_segment_2}}'] = getSub('type_segment_2', typeSeg, 1, `${core} Type 2`);
  payload['{{type_segment_3}}'] = getSub('type_segment_3', typeSeg, 2, `${core} Type 3`);

  payload['{{tech_segment_1}}'] = getSub('tech_segment_1', techSeg, 0, `${core} Tech 1`);
  payload['{{tech_segment_2}}'] = getSub('tech_segment_2', techSeg, 1, `${core} Tech 2`);
  payload['{{tech_segment_3}}'] = getSub('tech_segment_3', techSeg, 2, `${core} Tech 3`);

  payload['{{app_segment_1}}'] = getSub('app_segment_1', appSeg, 0, `${core} App 1`);
  payload['{{app_segment_2}}'] = getSub('app_segment_2', appSeg, 1, `${core} App 2`);
  payload['{{app_segment_3}}'] = getSub('app_segment_3', appSeg, 2, `${core} App 3`);
  payload['{{app_segment_4}}'] = getSub('app_segment_4', appSeg, 3, getSub('app_segment_1', appSeg, 0, `${core} App 4`));

  const seg4Name = endUserSeg ? endUserSeg.name : val('seg4_name', 'End User');
  payload['{{seg4_name}}'] = seg4Name;
  payload['{{seg4_sub1}}'] = getSub('seg4_sub1', endUserSeg, 0, `${seg4Name} 1`);
  payload['{{seg4_sub2}}'] = getSub('seg4_sub2', endUserSeg, 1, `${seg4Name} 2`);
  payload['{{seg4_sub3}}'] = getSub('seg4_sub3', endUserSeg, 2, `${seg4Name} 3`);

  const seg5Name = distSeg ? distSeg.name : val('seg5_name', 'Distribution Channel');
  payload['{{seg5_name}}'] = seg5Name;
  payload['{{seg5_sub1}}'] = getSub('seg5_sub1', distSeg, 0, `${seg5Name} 1`);
  payload['{{seg5_sub2}}'] = getSub('seg5_sub2', distSeg, 1, `${seg5Name} 2`);
  payload['{{seg5_sub3}}'] = getSub('seg5_sub3', distSeg, 2, `${seg5Name} 3`);
  payload['{{segment5_marketshare1}}'] = getSub('segment5_marketshare1', distSeg, 0, `${seg5Name} 1`);
  payload['{{segment5_marketshare2}}'] = getSub('segment5_marketshare2', distSeg, 1, `${seg5Name} 2`);
  payload['{{segment5_marketshare3}}'] = getSub('segment5_marketshare3', distSeg, 2, `${seg5Name} 3`);
  payload['{{segment5_marketshare4}}'] = getSub('segment5_marketshare4', distSeg, 3, getSub('segment5_marketshare1', distSeg, 0, `${seg5Name} 4`));

  const seg6Name = matSeg ? matSeg.name : val('seg6_name', 'Material');
  payload['{{seg6_name}}'] = seg6Name;
  payload['{{seg6_sub1}}'] = getSub('seg6_sub1', matSeg, 0, `${seg6Name} 1`);
  payload['{{seg6_sub2}}'] = getSub('seg6_sub2', matSeg, 1, `${seg6Name} 2`);
  payload['{{seg6_sub3}}'] = getSub('seg6_sub3', matSeg, 2, `${seg6Name} 3`);
  payload['{{segment6_marketshare1}}'] = getSub('segment6_marketshare1', matSeg, 0, `${seg6Name} 1`);
  payload['{{segment6_marketshare2}}'] = getSub('segment6_marketshare2', matSeg, 1, `${seg6Name} 2`);
  payload['{{segment6_marketshare3}}'] = getSub('segment6_marketshare3', matSeg, 2, `${seg6Name} 3`);
  payload['{{segment6_marketshare4}}'] = getSub('segment6_marketshare4', matSeg, 3, getSub('segment6_marketshare1', matSeg, 0, `${seg6Name} 4`));

  const customReqs = marketInput.custom_sections || [];
  for (let i = 1; i <= 4; i++) {
    const key = `{{ch4_custom_section_${i}_title}}`;
    if (customReqs.length >= i) {
      payload[key] = customReqs[i - 1].title || customReqs[i - 1];
    } else {
      payload[key] = `Client Requirement ${i}`;
    }
  }

  payload['{{ch4_custom_subsection_4_1_title}}'] = val('ch4_custom_subsection_4_1_title', 'Client Requirement 4.1');

  return payload;
}

async function renderReportDocx(templateBuffer, placeholderDict, adjustCoverTitle) {
  const zip = await JSZip.loadAsync(templateBuffer);
  const files = Object.keys(zip.files);

  for (const filename of files) {
    if (filename.endsWith('.xml') || filename.endsWith('.rels')) {
      let content = await zip.file(filename).async('text');

      const escapedDict = {};
      for (const [key, val] of Object.entries(placeholderDict)) {
        escapedDict[key] = String(val)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&apos;');
      }

      for (const [key, escapedVal] of Object.entries(escapedDict)) {
        if (content.includes(key)) {
          content = content.split(key).join(escapedVal);
        }
      }

      const tagPattern = '(?:<[^>]+>)*\\s*';
      for (const [key, escapedVal] of Object.entries(escapedDict)) {
        const rawKey = key.replace(/^\{\{|\}\}$/g, '').trim();
        if (!rawKey) continue;
        let patternStr = '\\{\\{\\s*';
        for (const ch of rawKey) {
          patternStr += ch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + tagPattern;
        }
        patternStr += '\\}\\}';
        const regex = new RegExp(patternStr, 'gi');
        content = content.replace(regex, escapedVal);
      }

      const splitRegex = /\{\{(?:<[^>]+>|[^}])*?\}\}/g;
      content = content.replace(splitRegex, (match) => {
        const cleanKey = '{{' + match.replace(/<[^>]+>/g, '').replace(/^\{\{|\}\}$/g, '').trim() + '}}';
        return escapedDict[cleanKey] !== undefined ? escapedDict[cleanKey] : '';
      });

      content = content.replace(/\{\{[^}]+\}\}/g, '');

      if (adjustCoverTitle && filename === 'word/document.xml') {
        content = content.replace(/w:sz w:val="88"/g, 'w:sz w:val="58"');
      }

      zip.file(filename, content);
    }
  }

  return await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
}

function getHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Content-Type': 'application/json',
  };
}

function buildFullPrompt(marketNameTitle, marketInput) {
  const core = extractCoreProductName(marketNameTitle);
  let segCtx = '';
  if (marketInput && marketInput.parsed_segments && marketInput.parsed_segments.length > 0) {
    segCtx = '\n=== EXTRACTED INPUT SEGMENTATIONS FROM USER DOCUMENT ===\n';
    for (const seg of marketInput.parsed_segments) {
      const subs = (seg.sub_segments || []).join(', ');
      segCtx += `- Dimension: ${seg.name} -> Sub-segments: ${subs}\n`;
    }
  }

  return `You are generating structured data fields for a ${core} market report template. The template has hardcoded narrative — you only need to supply short labels and names.

INPUT MARKET: "${marketNameTitle}"
CORE PRODUCT: "${core}"
${segCtx}

Generate a JSON object with these exact fields (all short strings, max lengths noted). All values MUST be real, specific, and realistic for the ${core} industry. Do NOT use generic placeholders like "Company 1" or "Standard Grade".

=== SEGMENT NAMES (for charts and tables) ===
type_segment_1 (max 30 chars): First sub-segment of type/product dimension.
type_segment_2 (max 35 chars): Second sub-segment of type/product dimension.
type_segment_3 (max 50 chars): Third sub-segment of type/product dimension.
tech_segment_1 (max 30 chars): First sub-segment of technology dimension.
tech_segment_2 (max 30 chars): Second sub-segment of technology dimension.
tech_segment_3 (max 40 chars): Third sub-segment of technology dimension.
app_segment_1 (max 30 chars): First sub-segment of application dimension (e.g. Professional Tournaments for Tennis Ball).
app_segment_2 (max 30 chars): Second sub-segment of application dimension (e.g. Recreational Leisure).
app_segment_3 (max 30 chars): Third sub-segment of application dimension (e.g. Fitness & Conditioning).
app_segment_4 (max 30 chars): Fourth sub-segment of application dimension.

=== COMPANY NAMES (real top companies in the ${core} industry, e.g. Wilson, Penn, Dunlop for Tennis Ball) ===
co1_name (max 20 chars): Top company in the ${core} industry.
co2_name (max 20 chars): Second major company in the ${core} industry.
co3_name (max 20 chars): Third company.
co4_name (max 30 chars): Fourth company.
co5_name (max 15 chars): Fifth company.
co6_name (max 15 chars): Sixth company.
co7_name (max 20 chars): Seventh company.
co8_name (max 15 chars): Eighth company.
co9_name (max 15 chars): Ninth company.
co10_name (max 15 chars): Tenth company.

=== CO1 SEGMENT NAMES ===
co1_segment_1_name (max 50 chars): Primary business segment for ${core}.
co1_segment_2_name (max 50 chars): Secondary business segment for ${core}.

=== SEGMENT 4/5/6 NAMES AND SUB-SEGMENTS ===
seg4_name (max 30 chars): Name of the 4th market dimension (e.g. Price Segment).
seg4_sub1 (max 30 chars): First sub-segment within seg4 (e.g. Premium).
seg4_sub2 (max 30 chars): Second sub-segment within seg4 (e.g. Mid-Range).
seg4_sub3 (max 30 chars): Third sub-segment within seg4 (e.g. Budget).
seg5_name (max 30 chars): Name of the 5th market dimension (e.g. Geography).
seg5_sub1 (max 30 chars): First sub-segment within seg5 (e.g. North America).
seg5_sub2 (max 30 chars): Second sub-segment within seg5 (e.g. Europe).
seg5_sub3 (max 30 chars): Third sub-segment within seg5 (e.g. Asia-Pacific).
seg6_name (max 30 chars): Name of the 6th market dimension (e.g. Distribution Channel).
seg6_sub1 (max 30 chars): First sub-segment within seg6 (e.g. Online Retail).
seg6_sub2 (max 30 chars): Second sub-segment within seg6 (e.g. Specialty Stores).
seg6_sub3 (max 30 chars): Third sub-segment within seg6 (e.g. Mass Market).

=== MARKET SHARE LABELS ===
segment5_marketshare1 (max 30 chars): Label for seg5 market share chart.
segment5_marketshare2 (max 30 chars): Label for seg5 market share chart.
segment5_marketshare3 (max 30 chars): Label for seg5 market share chart.
segment5_marketshare4 (max 30 chars): Label for seg5 market share chart.
segment6_marketshare1 (max 30 chars): Label for seg6 market share chart.
segment6_marketshare2 (max 30 chars): Label for seg6 market share chart.
segment6_marketshare3 (max 30 chars): Label for seg6 market share chart.
segment6_marketshare4 (max 30 chars): Label for seg6 market share chart.

=== CUSTOM SECTION ===
ch4_custom_subsection_4_1_title (max 50 chars): Title for custom subsection 4.1.

Return ONLY valid JSON starting with { and ending with }. No markdown, no code block formatting, no explanation.`;
}

function parseJsonResponse(contentStr) {
  if (!contentStr) return null;
  let jsonStr = contentStr.trim();
  if (jsonStr.includes('```')) {
    const parts = jsonStr.split('```');
    for (const part of parts) {
      const trimmed = part.trim();
      if (trimmed.startsWith('{') || trimmed.includes('{')) {
        jsonStr = trimmed;
        break;
      }
    }
  }
  const start = jsonStr.indexOf('{');
  const end = jsonStr.lastIndexOf('}');
  if (start !== -1 && end !== -1 && end > start) {
    jsonStr = jsonStr.slice(start, end + 1);
  }
  return JSON.parse(jsonStr);
}

exports.handler = async (event, context) => {
  const httpMethod = event.httpMethod || 'GET';

  if (httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers: getHeaders(), body: '' };
  }

  if (httpMethod === 'GET') {
    let samples = [];
    try {
      const files = fs.readdirSync(rootDir);
      samples = files.filter(f => f.endsWith('.docx') && !f.startsWith('~$') && !f.toLowerCase().includes('template'));
    } catch (e) {
      samples = ['Global_BESS_Market_Segmentation.docx', 'Global_Screw_Market_Segmentation.docx', 'Global_Soda_Market_Segmentation.docx', 'Sample_Green Methanol Market.docx'];
    }

    return {
      statusCode: 200,
      headers: getHeaders(),
      body: JSON.stringify({
        status: 'online',
        service: 'MarketIQ Report Generator API',
        samples: samples
      })
    };
  }

  if (httpMethod !== 'POST') {
    return { statusCode: 405, headers: getHeaders(), body: JSON.stringify({ error: 'Method not allowed' }) };
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
      return { statusCode: 400, headers: getHeaders(), body: JSON.stringify({ error: 'No file_data or sample_name provided' }) };
    }

    const marketInput = await parseDocxBuffer(inputBuffer);

    let aiContent = null;
    const keyToUse = api_key || process.env.OPENROUTER_API_KEY || config.openrouter_api_key;
    const modelName = process.env.MODEL || config.model || 'nvidia/nemotron-3-nano-30b-a3b:free';

    if (use_api !== false && keyToUse) {
      const MAX_RETRIES = 3;
      const RETRY_DELAY = 1000;
      const TIMEOUT_MS = 15000;

      for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
        try {
          const prompt = buildFullPrompt(marketInput.market_name_title, marketInput);
          console.log(`[AI] Attempt ${attempt}/${MAX_RETRIES} calling OpenRouter with model: ${modelName}`);
          const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
            signal: controller.signal,
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${keyToUse}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              model: modelName,
              messages: [{ role: 'user', content: prompt }]
            })
          });
          clearTimeout(timeoutId);
          if (res.ok) {
            const json = await res.json();
            const contentStr = json.choices[0].message ? json.choices[0].message.content : '';
            if (contentStr && contentStr.trim()) {
              aiContent = parseJsonResponse(contentStr);
              if (aiContent) {
                console.log(`[AI] Success on attempt ${attempt}/${MAX_RETRIES}`);
                break;
              } else {
                console.log(`[AI] Attempt ${attempt}/${MAX_RETRIES}: Parsed JSON was null or empty`);
              }
            } else {
              console.log(`[AI] Attempt ${attempt}/${MAX_RETRIES}: Empty response from API`);
            }
          } else {
            console.log(`[AI] Attempt ${attempt}/${MAX_RETRIES}: Response not ok, status: ${res.status}`);
          }
        } catch (e) {
          clearTimeout(timeoutId);
          console.log(`[AI] Attempt ${attempt}/${MAX_RETRIES} failed: ${e.message}`);
        }

        if (attempt < MAX_RETRIES) {
          console.log(`[AI] Retrying in ${RETRY_DELAY}ms...`);
          await new Promise(r => setTimeout(r, RETRY_DELAY));
        }
      }
    }

    if (!aiContent) {
      console.log('[AI] All attempts failed, falling back to generic content');
      aiContent = getFallbackContent(marketInput.market_name, marketInput);
    } else {
      console.log('[AI] Using AI-generated content');
    }

    const payload = buildPayload(aiContent, marketInput);

    const validation = validatePayload(payload);
    if (!validation.isValid) {
      console.warn('Payload validation warnings/errors:', validation.errors);
    }

    let templatePath = path.join(rootDir, config.template_file || 'full_market_report_template_updated.docx');
    if (!fs.existsSync(templatePath)) {
      templatePath = path.join(rootDir, 'templates', 'master_template_v1.docx');
    }
    if (!fs.existsSync(templatePath)) {
      templatePath = path.join(rootDir, 'full_market_report_template_updated.docx');
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
      api_model: config.model || process.env.MODEL || 'nvidia/nemotron-3-nano-30b-a3b:free',
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
