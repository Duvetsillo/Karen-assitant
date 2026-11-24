import { afterEach, describe, expect, it, vi } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { NativeVoice } from "../electron/voice";
import { defaults } from "../shared/settings";
import type { Settings } from '../shared/types';

const roots: string[] = [];
const profile = { profileId: "karen-test", referenceSha256: "a".repeat(64) };
function fixture(settings: Partial<Settings> = {}) {
  const root = mkdtempSync(join(tmpdir(), "karen-voice-"));
  roots.push(root);
  mkdirSync(join(root, "voice-models"));
  writeFileSync(join(root, "voice-models", "active-voice.json"), JSON.stringify({ id: profile.profileId, reference_sha256: profile.referenceSha256 }));
  writeFileSync(join(root, "voice-models", ".expressive-token"), "test-only-local-credential-".repeat(2));
  return new NativeVoice(root, () => ({ ...defaults, ttsEngine: "local", ...settings }));
}
afterEach(() => { vi.unstubAllGlobals(); roots.splice(0).forEach(root => rmSync(root, { recursive: true, force: true })); });

describe("voz compartida y fija", () => {
  it('prepara una sola vez con la identidad fija y sin enviar texto', async () => {
    const voice = fixture({voiceEnabled:true});
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json({protocol:2,...profile,capabilities:['prepare']}))
      .mockResolvedValueOnce(Response.json({ready:true,...profile}));
    vi.stubGlobal('fetch',fetcher);
    await Promise.all([voice.prepare(),voice.prepare()]);
    expect(fetcher).toHaveBeenCalledTimes(2);
    const [url,request]=fetcher.mock.calls[1];
    expect(url).toBe('http://127.0.0.1:18790/prepare');
    expect(JSON.parse(request.body)).toEqual(profile);
  });
  it('no precarga modelos al silenciar la voz o activar bajo consumo', async () => {
    const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);
    await fixture().prepare();
    await fixture({voiceEnabled:true,lowPower:true}).prepare();
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("envía el mismo perfil y valida la identidad del audio", async () => {
    const voice = fixture();
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ protocol: 2, ...profile }))
      .mockResolvedValueOnce(new Response("RIFFsynthetic-test", { headers: { "X-Karen-Voice-Id": profile.profileId, "X-Karen-Voice-Sha256": profile.referenceSha256, 'X-Karen-Voice-Style':'serene' } }));
    vi.stubGlobal("fetch", fetcher);
    expect(Buffer.from(await voice.synthesize("Hola Karen.")).toString()).toBe("RIFFsynthetic-test");
    const [url, request] = fetcher.mock.calls[1];
    expect(url).toBe("http://127.0.0.1:18790/speech");
    expect(JSON.parse(request.body)).toEqual({ text: "Hola Karen.", style:'serene', ...profile });
  });
  it('rechaza un servicio antiguo que ignore el estilo solicitado', async () => {
    const voice = fixture();
    vi.stubGlobal('fetch',vi.fn().mockResolvedValueOnce(Response.json({protocol:2,...profile}))
      .mockResolvedValueOnce(new Response('RIFFfixture',{headers:{'X-Karen-Voice-Id':profile.profileId,'X-Karen-Voice-Sha256':profile.referenceSha256}})));
    await expect(voice.synthesize('Hola')).rejects.toThrow('Actualiza');
  });
  it("rechaza otra identidad sin cambiar al motor de Windows", async () => {
    const voice = fixture();
    const fetcher = vi.fn().mockResolvedValue(Response.json({ protocol: 2, ...profile, profileId: "another-voice" }));
    vi.stubGlobal("fetch", fetcher);
    await expect(voice.synthesize("Hola")).rejects.toThrow("otro perfil");
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it("rechaza un servicio que niega autenticación y un audio de otro perfil", async () => {
    const voice = fixture();
    const fetcher = vi.fn().mockResolvedValueOnce(new Response("Forbidden", { status: 403 }));
    vi.stubGlobal("fetch", fetcher);
    await expect(voice.synthesize("Hola")).rejects.toThrow("403");
    fetcher.mockResolvedValueOnce(Response.json({ protocol: 2, ...profile }))
      .mockResolvedValueOnce(new Response("RIFFwrong-voice", { headers: { "X-Karen-Voice-Id": "another-voice" } }));
    await expect(voice.synthesize("Hola")).rejects.toThrow("voz fija");
  });
  it("cancelar descarta la petición pendiente", async () => {
    const voice = fixture();
    const fetcher = vi.fn().mockImplementation((_url: string, options: RequestInit) => new Promise((_resolve, reject) => {
      options.signal?.addEventListener("abort", () => reject(new DOMException("Cancelled", "AbortError")));
    }));
    vi.stubGlobal("fetch", fetcher);
    const pending = voice.synthesize("Hola");
    voice.cancel();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  });
  it("distingue el motor detenido de un rechazo de autenticación sin iniciarlo", async () => {
    const voice = fixture();
    mkdirSync(join(roots.at(-1)!, "expressive-runtime", "Scripts"), { recursive: true });
    writeFileSync(join(roots.at(-1)!, "expressive-runtime", "Scripts", "python.exe"), "fixture-not-executable");
    const fetcher = vi.fn().mockRejectedValueOnce(new TypeError("fetch failed"));
    vi.stubGlobal("fetch", fetcher);
    expect(await voice.health()).toContain("se inicia al hablar");
    fetcher.mockResolvedValueOnce(new Response("Forbidden", { status: 403 }));
    expect(await voice.health()).toContain("403");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
