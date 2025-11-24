import Foundation

#if DEBUG
extension SecretsProvider {
    /// Quick verification that secrets are loading correctly
    /// Call this in your app's init or a debug menu to confirm setup
    static func verify() -> (hasKey: Bool, hasModel: Bool, keyPrefix: String) {
        let provider = SecretsProvider()
        let key = provider.apiKey
        return (
            hasKey: !key.isEmpty,
            hasModel: provider.preferredModel != nil,
            keyPrefix: key.isEmpty ? "" : String(key.prefix(7)) + "..."
        )
    }
}
#endif