/*
Copyright 2025 Google Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

// Implementing a custom file processor is necessary to support these changes:
// - Loop a single frame for N times, or infinitely

// NOLINT(build/header_guard)
#ifndef GFXRECON_DECODE_DIVE_FILE_PROCESSOR_H
#define GFXRECON_DECODE_DIVE_FILE_PROCESSOR_H

#include <memory>

#include "decode/file_processor.h"

#include "dive_block_data.h"

GFXRECON_BEGIN_NAMESPACE(gfxrecon)
GFXRECON_BEGIN_NAMESPACE(decode)

class DiveFileProcessor : public FileProcessor
{
public:
    void SetDiveBlockData(std::shared_ptr<DiveBlockData> p_block_data);

    // Writes content to a new file that is put in the same dir as the capture file,
    // overwriting existing file if present
    bool WriteFile(const std::string& name, const std::string& content);

protected:
    void StoreBlockInfo() override;

private:
    // The DiveBlockData object that contains the metadata for the original GFXR file and
    // modifications
    std::shared_ptr<DiveBlockData> dive_block_data_ = nullptr;

    // Need to store this because the active file is sometimes the .gfxa one
    std::string gfxr_file_name_ = "";
};

GFXRECON_END_NAMESPACE(decode)
GFXRECON_END_NAMESPACE(gfxrecon)

#endif  // GFXRECON_DECODE_DIVE_FILE_PROCESSOR_H
