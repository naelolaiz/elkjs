/*******************************************************************************
 * Copyright (c) 2024 Kiel University and others.
 *
 * This program and the accompanying materials are made
 * available under the terms of the Eclipse Public License 2.0
 * which is available at https://www.eclipse.org/legal/epl-2.0/
 *
 * SPDX-License-Identifier: EPL-2.0
 *******************************************************************************/
// Bridge script for Python-to-Node.js communication.
// Reads JSON commands from stdin (one per line), processes them with the
// ELK worker, and writes JSON responses to stdout (one per line).

'use strict';

var path = require('path');
var readline = require('readline');

var workerPath = process.argv[2];
if (!workerPath) {
    process.stderr.write('Usage: node _bridge.js <path-to-elk-worker.js>\n');
    process.exit(1);
}

var workerModule = require(path.resolve(workerPath));
var Worker = workerModule.Worker;
var worker = new Worker();

// Flatten GWT-style errors that contain circular references.
// This mirrors the convertGwtStyleError logic in elk-api.js.
function convertGwtStyleError(err) {
    if (!err) return;
    var javaException = err['__java$exception'];
    if (javaException) {
        if (javaException.cause && javaException.cause.backingJsObject) {
            err.cause = javaException.cause.backingJsObject;
            convertGwtStyleError(err.cause);
        }
        delete err['__java$exception'];
    }
}

// Serialise an error safely (Error objects have circular refs after GWT).
function serialiseError(err) {
    if (!err) return null;
    convertGwtStyleError(err);
    var obj = { message: err.message || String(err) };
    if (err.cause) {
        obj.cause = serialiseError(err.cause);
    }
    return obj;
}

worker.onmessage = function (answer) {
    var json = answer.data;
    var response;
    if (json.error) {
        response = { id: json.id, error: serialiseError(json.error) };
    } else {
        response = { id: json.id, data: json.data };
    }
    process.stdout.write(JSON.stringify(response) + '\n');
};

var rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });

rl.on('line', function (line) {
    if (!line.trim()) return;
    try {
        var msg = JSON.parse(line);
        worker.postMessage(msg);
    } catch (e) {
        process.stdout.write(JSON.stringify({ id: null, error: { message: e.message } }) + '\n');
    }
});

// When stdin closes, let pending callbacks drain before exiting.
// Do NOT call process.exit() here — that would kill async worker replies.
