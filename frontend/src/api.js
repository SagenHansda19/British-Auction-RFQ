
export function getUserId() {
  return localStorage.getItem("userId");
}

export function setUserId(id) {
  localStorage.setItem("userId", id);
}

async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const userId = getUserId();
  if (userId) headers["X-User-Id"] = userId;

  const response = await fetch(`/api/v1${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json();

  if (!response.ok) {
    const error = data.error;
    const fieldErrors = (error.details || []).map((d) => `${d.field}: ${d.msg}`).join("; ");
    throw new Error(fieldErrors ? `${error.message} (${fieldErrors})` : error.message);
  }
  return data;
}

export const api = {
  getUsers: () => request("/users"),
  getRfqs: (status) => request(status ? `/rfqs?status=${status}` : "/rfqs"),
  getRfq: (id) => request(`/rfqs/${id}`),
  getEvents: (id) => request(`/rfqs/${id}/events`),
  createRfq: (body) => request("/rfqs", { method: "POST", body }),
  placeBid: (id, body) => request(`/rfqs/${id}/bids`, { method: "POST", body }),
};
