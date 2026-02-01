class Tracetap < Formula
  include Language::Python::Virtualenv

  desc "HTTP/HTTPS traffic capture proxy with AI-powered API analysis and testing tools"
  homepage "https://github.com/VassilisSoum/tracetap"
  url "https://files.pythonhosted.org/packages/source/t/tracetap/tracetap-1.0.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256_HASH"  # Update with actual hash
  license "MIT"
  head "https://github.com/VassilisSoum/tracetap.git", branch: "master"

  depends_on "python@3.11"

  resource "mitmproxy" do
    url "https://files.pythonhosted.org/packages/source/m/mitmproxy/mitmproxy-10.1.6.tar.gz"
    sha256 "PLACEHOLDER_MITMPROXY_SHA256"
  end

  resource "anthropic" do
    url "https://files.pythonhosted.org/packages/source/a/anthropic/anthropic-0.71.0.tar.gz"
    sha256 "PLACEHOLDER_ANTHROPIC_SHA256"
  end

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/PyYAML-6.0.1.tar.gz"
    sha256 "bfdf460b1736c775f2ba9f6a92bca30bc2095067b8a9d77876d1fad6cc3b4a43"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/source/t/typing_extensions/typing_extensions-4.11.0.tar.gz"
    sha256 "83f085bd5ca59c80295fc2a82ab5dac679cbe02b9f33f7d83af68e241bea51b0"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    # Test that tracetap command is available
    assert_match "TraceTap", shell_output("#{bin}/tracetap --help")

    # Test version command
    assert_match version.to_s, shell_output("#{bin}/tracetap --version")

    # Test other CLI commands are available
    assert_match "AI-powered", shell_output("#{bin}/tracetap-ai-postman --help")
    assert_match "replay", shell_output("#{bin}/tracetap-replay --help")
    assert_match "Playwright", shell_output("#{bin}/tracetap-playwright --help")
  end
end
