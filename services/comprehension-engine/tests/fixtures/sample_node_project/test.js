const request = require("supertest");
const app = require("./index");

describe("health", () => {
  it("returns ok", async () => {
    const response = await request(app).get("/health");
    expect(response.statusCode).toBe(200);
  });
});
