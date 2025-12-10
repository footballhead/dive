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

// Implementing a custom file processor for Dive

#include "dive_file_processor.h"

#include "util/logging.h"
#include "util/platform.h"

#include "dive_block_data.h"

GFXRECON_BEGIN_NAMESPACE(gfxrecon)
GFXRECON_BEGIN_NAMESPACE(decode)

void DiveFileProcessor::SetDiveBlockData(std::shared_ptr<DiveBlockData> p_block_data)
{
    dive_block_data_ = p_block_data;

    // When populating DiveBlockData we want to run through the entire file.
    run_without_decoders_ = true;
}

bool DiveFileProcessor::WriteFile(const std::string& name, const std::string& content)
{
    std::string new_file_path = absolute_path_ + "/" + name;

    FILE* fd;
    int   result = util::platform::FileOpen(&fd, new_file_path.c_str(), "wb");
    if (result || fd == nullptr)
    {
        GFXRECON_LOG_ERROR("Failed to open file %s, exit code: %d", new_file_path.c_str(), result);
        return false;
    }

    bool res = util::platform::FilePuts(content.c_str(), fd);
    if (!res)
    {
        GFXRECON_LOG_ERROR("Could not write file: %s", new_file_path.c_str());
    }

    GFXRECON_LOG_INFO("Wrote file: %s", new_file_path.c_str());

    result = util::platform::FileClose(fd);
    if (result)
    {
        GFXRECON_LOG_ERROR("Failed to close file %s, exit code: %d", new_file_path.c_str(), result);
        return false;
    }

    return true;
}

void DiveFileProcessor::StoreBlockInfo()
{
    if (gfxr_file_name_.empty())
    {
        // Assuming that the first time StoreBlockInfo() is called, the active file is .gfxr file
        gfxr_file_name_ = GetActiveFilename();
        GFXRECON_LOG_INFO("Storing active filename %s", gfxr_file_name_.c_str());
    }

    if (!dive_block_data_)
    {
        return;
    }

    int64_t offset = TellFile(gfxr_file_name_);
    GFXRECON_ASSERT(offset > 0);
    dive_block_data_->AddOriginalBlock(block_index_, static_cast<uint64_t>(offset));
}

GFXRECON_END_NAMESPACE(decode)
GFXRECON_END_NAMESPACE(gfxrecon)
