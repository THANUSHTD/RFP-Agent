const BASE_URL = 'http://localhost:8000';

async function handleResponse(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error');
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res;
}

// ─── Health ──────────────────────────────────────────────────────────────────
export async function getHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getHealth error:', e);
    return null;
  }
}

// ─── Sessions ─────────────────────────────────────────────────────────────────
export async function getSessions() {
  try {
    const res = await fetch(`${BASE_URL}/sessions`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getSessions error:', e);
    return [];
  }
}

export async function createSession(name) {
  try {
    const res = await fetch(`${BASE_URL}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('createSession error:', e);
    return null;
  }
}

// ─── Session Messages ─────────────────────────────────────────────────────────
export async function getMessages(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/messages`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getMessages error:', e);
    return [];
  }
}

export async function sendChat(sessionId, content) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('sendChat error:', e);
    return null;
  }
}

// ─── RFP Upload & Analyze ─────────────────────────────────────────────────────
export async function uploadRFP(sessionId, file) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/rfp`, {
      method: 'POST',
      body: formData,
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('uploadRFP error:', e);
    return null;
  }
}

export async function analyzeRFP(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/analyze`, {
      method: 'POST',
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('analyzeRFP error:', e);
    return null;
  }
}

// ─── Questions ────────────────────────────────────────────────────────────────
export async function getQuestions(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/questions`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getQuestions error:', e);
    return [];
  }
}

export async function getAnswer(questionId) {
  try {
    const res = await fetch(`${BASE_URL}/questions/${questionId}/answer`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getAnswer error:', e);
    return null;
  }
}

export async function patchAnswer(questionId, text) {
  try {
    const res = await fetch(`${BASE_URL}/questions/${questionId}/answer`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('patchAnswer error:', e);
    return null;
  }
}

export async function approveAnswer(questionId) {
  try {
    const res = await fetch(`${BASE_URL}/questions/${questionId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true }),
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('approveAnswer error:', e);
    return null;
  }
}

// ─── Clarifications ───────────────────────────────────────────────────────────
export async function getClarifications(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/clarifications`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getClarifications error:', e);
    return [];
  }
}

// ─── Format Rules ─────────────────────────────────────────────────────────────
export async function getFormatRules(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/format-rules`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getFormatRules error:', e);
    return null;
  }
}

export async function putFormatRules(sessionId, rules, confirmed_by_se) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/format-rules`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rules, confirmed_by_se }),
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('putFormatRules error:', e);
    return null;
  }
}

// ─── Export ───────────────────────────────────────────────────────────────────
export async function triggerExport(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/export`, {
      method: 'POST',
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('triggerExport error:', e);
    return null;
  }
}

export async function downloadExportDocx(sessionId, filename) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/export/docx`);
    await handleResponse(res);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `rfp_proposal_${sessionId}.docx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('downloadExportDocx error:', e);
  }
}

export async function downloadExportXlsx(sessionId, filename) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/export/xlsx`);
    await handleResponse(res);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `rfp_matrix_${sessionId}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('downloadExportXlsx error:', e);
  }
}

// ─── Knowledge Base ───────────────────────────────────────────────────────────
export async function getKBDocuments() {
  try {
    const res = await fetch(`${BASE_URL}/kb/documents`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getKBDocuments error:', e);
    return [];
  }
}

export async function ingestKB() {
  try {
    const res = await fetch(`${BASE_URL}/kb/ingest`, {
      method: 'POST',
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('ingestKB error:', e);
    return null;
  }
}

// ─── Level 2: Compliance / Response Codes ─────────────────────────────────────
export async function getComplianceMatrix(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/compliance-matrix`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getComplianceMatrix error:', e);
    return null;
  }
}

export async function getResponseCodes(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/response-codes`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getResponseCodes error:', e);
    return [];
  }
}

export async function getResponseCode(sessionId, questionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/questions/${questionId}/response-code`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getResponseCode error:', e);
    return null;
  }
}

export async function putResponseCode(sessionId, questionId, body) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/questions/${questionId}/response-code`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('putResponseCode error:', e);
    return null;
  }
}

// ─── Level 2: Gap Analysis ────────────────────────────────────────────────────
export async function getGaps(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/gaps`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getGaps error:', e);
    return { gaps: [], total: 0, high_severity: 0, confirmed_gaps: 0, knowledge_gaps: 0 };
  }
}

export async function regenerateGaps(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/gaps/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: true }),
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('regenerateGaps error:', e);
    return null;
  }
}

// ─── Level 2: Response Validation ─────────────────────────────────────────────
export async function getValidation(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/validation`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getValidation error:', e);
    return { issues: [], total: 0, high_severity: 0, medium_severity: 0 };
  }
}

export async function regenerateValidation(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/validation/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force: true }),
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('regenerateValidation error:', e);
    return null;
  }
}

// ─── Level 2: Submission Checklist ────────────────────────────────────────────
export async function getChecklist(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/checklist`);
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('getChecklist error:', e);
    return { items: [], total: 0, done: 0, pending: 0, percent: 0 };
  }
}

export async function regenerateChecklist(sessionId) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/checklist/regenerate`, {
      method: 'POST',
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('regenerateChecklist error:', e);
    return null;
  }
}

export async function putChecklistItem(sessionId, itemKey, body) {
  try {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/checklist/${itemKey}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    await handleResponse(res);
    return await res.json();
  } catch (e) {
    console.error('putChecklistItem error:', e);
    return null;
  }
}
