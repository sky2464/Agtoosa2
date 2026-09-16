# typed: false
# frozen_string_literal: true

class Agtoosa < Formula
  desc "Unified Graph-Native Engineering Operating System"
  homepage "https://github.com/sky2464/Agtoosa2"
  version "0.9.6"
  license "MIT"

  on_macos do
    if Hardware::CPU.arm?
      url "https://github.com/sky2464/Agtoosa2/releases/download/v#{version}/agtoosa-v#{version}-darwin-arm64.tar.gz"
      sha256 "PLACEHOLDER_DARWIN_ARM64_SHA256"
    else
      url "https://github.com/sky2464/Agtoosa2/releases/download/v#{version}/agtoosa-v#{version}-darwin-x86_64.tar.gz"
      sha256 "PLACEHOLDER_DARWIN_X86_64_SHA256"
    end
  end

  on_linux do
    if Hardware::CPU.intel?
      url "https://github.com/sky2464/Agtoosa2/releases/download/v#{version}/agtoosa-v#{version}-linux-x86_64.tar.gz"
      sha256 "PLACEHOLDER_LINUX_X86_64_SHA256"
    end
  end

  def install
    bin.install "agtoosa"
  end

  test do
    assert_match "Agtoosa2", shell_output("#{bin}/agtoosa version")
  end
end
