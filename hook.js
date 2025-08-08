// ==UserScript==
// @name         hook getDivideCountDown
// @namespace    http://tampermonkey.net/
// @version      2025-08-06
// @description  try to take over the world!
// @author       tbjuechen
// @match        http://*/*
// @icon         data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==
// @grant        none
// ==/UserScript==

(function () {
    // Hook fetch
    const originalFetch = window.fetch;
    window.fetch = async function (...args) {
        if (args[0].includes('/getDivideCountDown')) {
            console.log("伪造响应触发 fetch", args);
            return Promise.resolve(new Response(JSON.stringify({
                "msg": "success",
                "code": 0,
                "divideCountDown": {
                    "start": 1754467200000,
                    "bedStatus": 2,
                    "end": 1754640000000,
                    "planId": "fc725da11d34af1f1b12cafd4f8568cc",
                    "id": "08a1be8166659a7dd7dc79256ee83c97"
                }
            }), {
                status: 200,
                headers: { "Content-Type": "application/json" }
            }));
        }
        return originalFetch.apply(this, args);
    };

    // Hook XMLHttpRequest
    const open = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (method, url, ...rest) {
        this._url = url;
        return open.call(this, method, url, ...rest);
    };

    const send = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function (...args) {
        const xhr = this;
        const origOnReadyStateChange = xhr.onreadystatechange;
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 && xhr._url.includes('/getDivideCountDown')) {
                console.log("伪造响应触发 xhr", xhr._url);
                Object.defineProperty(xhr, 'responseText', {
                    get: () => JSON.stringify({
                        "msg": "success",
                        "code": 0,
                        "divideCountDown": {
                            "start": 1754467200000,
                            "bedStatus": 2,
                            "end": 1754640000000,
                            "planId": "fc725da11d34af1f1b12cafd4f8568cc",
                            "id": "08a1be8166659a7dd7dc79256ee83c97"
                        }
                    })
                });
            }
            if (origOnReadyStateChange) origOnReadyStateChange.apply(this, arguments);
        };
        return send.apply(this, args);
    };
})();
