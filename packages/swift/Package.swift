// swift-tools-version: 6.0
// Copyright 2026 The uni-llm-client Authors
// SPDX-License-Identifier: Apache-2.0

import PackageDescription

let package = Package(
    name: "UniLLMClient",
    platforms: [.macOS(.v13), .iOS(.v16), .tvOS(.v16), .watchOS(.v9), .visionOS(.v1)],
    products: [
        .library(name: "UniLLMClient", targets: ["UniLLMClient"])
    ],
    // Foundation is the only dependency. See CONTRIBUTING.md.
    targets: [
        .target(name: "UniLLMClient"),
        .testTarget(name: "UniLLMClientTests", dependencies: ["UniLLMClient"]),
    ]
)
