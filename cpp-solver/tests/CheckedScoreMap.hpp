#pragma once

#include <cstddef>
#include <memory>
#include <stdexcept>
#include <unordered_map>

namespace test_support {
inline std::size_t score_map_rehashes = 0;

// Test-only wrapper: make standard iterator invalidation deterministic to detect.
// It otherwise preserves the real unordered_map's insertion and rehash behavior.
template <typename Key, typename Value, typename Hash>
class CheckedScoreMap {
    using Map = std::unordered_map<Key, Value, Hash>;
    Map values_;
    std::size_t epoch_ = 0;

public:
    class iterator {
        CheckedScoreMap* owner_;
        typename Map::iterator iterator_;
        std::size_t epoch_;

        void check() const {
            if (epoch_ != owner_->epoch_) {
                throw std::logic_error("score-map iterator used after rehash");
            }
        }

    public:
        iterator(CheckedScoreMap* owner, typename Map::iterator value)
            : owner_(owner), iterator_(value), epoch_(owner->epoch_) {}

        typename Map::value_type* operator->() const {
            check();
            return std::addressof(*iterator_);
        }

        bool operator==(const iterator& other) const {
            check();
            other.check();
            return iterator_ == other.iterator_;
        }
    };

    iterator find(const Key& key) { return iterator(this, values_.find(key)); }
    iterator end() { return iterator(this, values_.end()); }

    Value& operator[](const Key& key) {
        const auto previous_buckets = values_.bucket_count();
        Value& value = values_[key];
        if (values_.bucket_count() != previous_buckets) {
            ++epoch_;
            ++score_map_rehashes;
        }
        return value;
    }
};
} // namespace test_support
